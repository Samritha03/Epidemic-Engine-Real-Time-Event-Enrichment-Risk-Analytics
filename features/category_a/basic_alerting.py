"""
Phase 3 - Category A1: Basic Real-Time Alerting

Monitors two metrics from Postgres:
  1) Total symptom events per region in the last N minutes
  2) Percentage of severe events in the last N minutes

If thresholds are exceeded, sends a human-readable alert via:
  - Slack webhook (if ALERT_WEBHOOK_URL is set), or
  - Console logging as a fallback.

Run locally with port-forward:
  1) oc port-forward svc/postgres 5432:5432
  2) conda activate ds551
  3) python features/category_a/basic_alerting.py
"""

import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# DB + alert utilities

def get_engine():
    """Create a SQLAlchemy engine using environment variables."""
    load_dotenv()

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "epidemic")
    user = os.getenv("DB_USER", "ds551")
    password = os.getenv("DB_PASSWORD", "ds551pw")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(url)


def send_alert(message: str):
    """
    Send an alert.

    If ALERT_WEBHOOK_URL is set, POST to that URL.
    Otherwise, print to stdout (still useful for grading/demo).
    """
    webhook = os.getenv("ALERT_WEBHOOK_URL", "").strip()

    print("\n=== [ALERT] ===")
    print(message)
    print("==============\n")

    if webhook:
        try:
            resp = requests.post(webhook, json={"text": message}, timeout=5)
            print(f"[alert] Sent to webhook, status={resp.status_code}")
        except Exception as e:
            print(f"[alert] Failed to send to webhook: {e}")


# Metric computation

def fetch_region_events(engine, lookback_minutes: int = 5) -> pd.DataFrame:
    query = text(
        """
        SELECT
            region,
            SUM(event_count) AS events_5m
        FROM symptom_by_region
        WHERE region IS NOT NULL
        AND last_updated >= NOW() - (:lookback * INTERVAL '1 minute')
        GROUP BY region
        ORDER BY events_5m DESC;
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"lookback": lookback_minutes})

    return df


def fetch_severity_share(engine, lookback_minutes: int = 5) -> pd.DataFrame:
    query = text(
        """
        SELECT
            severity,
            SUM(event_count) AS total_events
        FROM severity_distribution
        WHERE last_updated >= NOW() - (:lookback * INTERVAL '1 minute')
        GROUP BY severity;
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"lookback": lookback_minutes})

    if df.empty:
        return df

    total = df["total_events"].sum()
    df["percentage"] = (df["total_events"] / total) * 100.0
    return df


# Threshold checks

def check_thresholds(region_df: pd.DataFrame,
                     severity_df: pd.DataFrame,
                     region_event_threshold: int = 500,
                     severe_pct_threshold: float = 40.0):
    """
    Evaluate metrics and fire alerts when thresholds are crossed.
    """

    # Metric 1: high total events per region
    if not region_df.empty:
        hot_regions = region_df[region_df["events_5m"] >= region_event_threshold]
    else:
        hot_regions = pd.DataFrame()

    # Metric 2: high severe share
    severe_row = None
    if not severity_df.empty:
        severe_row = severity_df[severity_df["severity"] == "severe"]
    severe_pct = float(severe_row["percentage"].iloc[0]) if severe_row is not None and not severe_row.empty else 0.0

    alerts = []

    # Build alert messages (simple, human-readable)
    if not hot_regions.empty:
        region_lines = [
            f"- {row.region}: {int(row.events_5m)} events in last 5 minutes"
            for _, row in hot_regions.iterrows()
        ]
        msg = (
            f"[Basic Alert] High visit volume detected\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}Z\n"
            f"Threshold: {region_event_threshold} events / 5 min\n"
            f"Regions:\n" + "\n".join(region_lines)
        )
        alerts.append(msg)

    if severe_pct >= severe_pct_threshold:
        msg = (
            f"[Basic Alert] High severe case share detected\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}Z\n"
            f"Severe share: {severe_pct:.1f}% (threshold={severe_pct_threshold:.1f}%)"
        )
        alerts.append(msg)

    for msg in alerts:
        send_alert(msg)


# Main polling loop

def run_basic_alerting(poll_interval_seconds: int = 60):
    """
    Poll the database in a simple loop and fire alerts when needed.
    Ctrl+C to stop.
    """
    engine = get_engine()
    print("=== Basic Real-Time Alerting (A1) ===")
    print(f"Polling every {poll_interval_seconds} seconds. Ctrl+C to exit.")

    try:
        while True:
            try:
                region_df = fetch_region_events(engine, lookback_minutes=5)
                severity_df = fetch_severity_share(engine, lookback_minutes=5)

                check_thresholds(
                    region_df,
                    severity_df,
                    region_event_threshold=500,
                    severe_pct_threshold=40.0,
                )
            except Exception as e:
                print(f"[basic-alert] Error during polling: {e}")

            time.sleep(poll_interval_seconds)
    except KeyboardInterrupt:
        print("\nStopped basic alerting loop.")


if __name__ == "__main__":
    run_basic_alerting(poll_interval_seconds=60)
