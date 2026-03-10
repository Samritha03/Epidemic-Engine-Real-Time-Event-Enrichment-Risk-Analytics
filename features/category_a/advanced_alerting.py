"""
Phase 3 - Category A2: Advanced Real-Time Alerting

- Monitors recent symptom volume from `symptom_by_region`.
- Computes Z-scores to detect unusually high activity.
- Adds severity levels (MEDIUM / HIGH) based on max Z-score.
- Aggregates all hot regions into a single alert message.
- Applies a cooldown so we don't spam alerts.
- Reads thresholds + cooldown from advanced_alert_config.json.
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# Configuration helpers

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "advanced_alert_config.json"
)


def load_config() -> dict:
    """Load advanced alerting configuration from JSON file."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


# DB + webhook utilities

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


def get_webhook_url() -> str | None:
    load_dotenv()
    return os.getenv("ALERT_WEBHOOK_URL")


def send_alert(message: str, severity: str, webhook_url: str | None):
    """
    Send alert to stdout and (optionally) to Slack via webhook.
    """
    header = f"=== [ADVANCED ALERT - {severity}] ==="
    print(header)
    print(message)
    print("=" * len(header))

    if webhook_url:
        try:
            resp = requests.post(webhook_url, json={"text": message}, timeout=5)
            print(f"[advanced-alert] Sent to webhook, status={resp.status_code}")
        except Exception as exc:
            print(f"[advanced-alert] Error sending to webhook: {exc}")


# Data fetch functions

def fetch_region_events(engine, lookback_minutes: int = 5) -> pd.DataFrame:
    """
    Aggregate recent event counts by region over the lookback window.
    """
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
    """
    Aggregate severity counts over the lookback window and compute shares.
    """
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


# Alerting logic

def classify_severity(df: pd.DataFrame, cfg: dict) -> str:
    """
    Use Z-score of events_5m to assign an overall severity level.

    - HIGH   if max Z >= z_high
    - MEDIUM if max Z >= z_medium
    - LOW    otherwise
    """
    if df.empty:
        return "LOW"

    mean = df["events_5m"].mean()
    std = df["events_5m"].std(ddof=0)
    if std == 0 or pd.isna(std):
        # No variance → treat as LOW but still allowed to alert based on volume
        return "LOW"

    df["z_score"] = (df["events_5m"] - mean) / std
    z_max = df["z_score"].max()

    if z_max >= cfg.get("z_high", 1.5):
        return "HIGH"
    if z_max >= cfg.get("z_medium", 0.5):
        return "MEDIUM"
    return "LOW"


def build_alert_message(
    hot_regions: pd.DataFrame,
    severity_mix: pd.DataFrame,
    cfg: dict,
    severity_level: str,
) -> str:
    """
    Build a human-readable alert message summarizing advanced metrics.
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    lines: list[str] = []
    lines.append("[Advanced Alert] Unusual symptom activity detected")
    lines.append(f"Time: {now_utc}")
    lines.append(
        f"Lookback window: last {cfg['lookback_minutes']} minutes "
        f"(threshold={cfg['volume_threshold']} events)"
    )
    lines.append(f"Assigned severity: {severity_level}")
    lines.append("")

    # Top regions
    lines.append("Regions with elevated activity:")
    for _, row in hot_regions.iterrows():
        region = row["region"]
        events = int(row["events_5m"])
        z = row.get("z_score", float("nan"))
        lines.append(f"- {region}: {events} events (z={z:.2f})")

    lines.append("")

    # Severity mix summary
    if not severity_mix.empty:
        lines.append("Severity mix in lookback window:")
        for _, row in severity_mix.iterrows():
            sev = row["severity"]
            pct = row["percentage"]
            lines.append(f"- {sev}: {pct:.1f}%")
    else:
        lines.append("Severity mix: no data available.")

    return "\n".join(lines)


def poll_loop(engine, cfg: dict, webhook_url: str | None):
    """
    Main polling loop:

    - Fetch region aggregates + severity mix.
    - Decide severity level.
    - If MEDIUM / HIGH and outside cooldown, send alert.
    """
    lookback = cfg["lookback_minutes"]
    volume_thresh = cfg["volume_threshold"]
    poll_interval = cfg["poll_interval_seconds"]
    cooldown = timedelta(minutes=cfg["cooldown_minutes"])
    top_n = cfg.get("top_n_regions", 5)

    last_alert_time: datetime | None = None

    print("=== Advanced Real-Time Alerting (A2) ===")
    print(
        f"Polling every {poll_interval} seconds, "
        f"lookback={lookback} minutes, cooldown={cooldown}."
    )
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            df_regions = fetch_region_events(engine, lookback_minutes=lookback)
            if df_regions.empty:
                print("[advanced-alert] No region data; sleeping.")
                time.sleep(poll_interval)
                continue

            # Censor to regions that exceed base volume threshold
            hot = df_regions[df_regions["events_5m"] >= volume_thresh].copy()
            if hot.empty:
                print(
                    "[advanced-alert] No regions above volume threshold; "
                    "sleeping."
                )
                time.sleep(poll_interval)
                continue

            # Classify severity based on Z-score
            severity_level = classify_severity(hot, cfg)

            now = datetime.now(timezone.utc)
            if last_alert_time is not None and now - last_alert_time < cooldown:
                # Suppression / cooldown in effect
                remaining = cooldown - (now - last_alert_time)
                print(
                    f"[advanced-alert] {severity_level} alert suppressed "
                    f"(cooldown {remaining} remaining)."
                )
                time.sleep(poll_interval)
                continue

            # Compute severity mix
            sev_mix = fetch_severity_share(engine, lookback_minutes=lookback)

            # Sort & truncate regions for message
            hot_sorted = hot.sort_values("events_5m", ascending=False).head(top_n)

            msg = build_alert_message(
                hot_regions=hot_sorted,
                severity_mix=sev_mix,
                cfg=cfg,
                severity_level=severity_level,
            )

            send_alert(msg, severity_level, webhook_url)
            last_alert_time = now

        except KeyboardInterrupt:
            print("\n[advanced-alert] Stopping on user request.")
            break
        except Exception as exc:
            print(f"[advanced-alert] Error during polling: {exc}")
            time.sleep(poll_interval)


# Entry point

def main():
    cfg = load_config()
    engine = get_engine()
    webhook_url = get_webhook_url()

    poll_loop(engine, cfg, webhook_url)


if __name__ == "__main__":
    main()
