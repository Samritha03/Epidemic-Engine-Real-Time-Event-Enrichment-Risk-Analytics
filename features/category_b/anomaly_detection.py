"""
Phase 3 - Category B1: Anomaly Detection

Reads aggregated metrics from the `symptom_by_region` table,
computes a Z-score on event_count, and writes anomalous rows
into an `anomalies` table in Postgres.

Run locally (with oc port-forward) or inside OpenShift.
"""

import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


# DB utilities

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


def fetch_symptom_by_region(engine) -> pd.DataFrame:
    """
    Load current aggregated data from symptom_by_region.

    Expected columns:
      - region
      - symptoms
      - event_count
      - avg_severity_score
      - last_updated
    """
    query = """
        SELECT
            region,
            symptoms,
            event_count,
            avg_severity_score,
            last_updated
        FROM symptom_by_region
        WHERE event_count IS NOT NULL;
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df


# Anomaly detection logic

def compute_anomalies(df: pd.DataFrame, z_threshold: float = 2.5) -> pd.DataFrame:
    """
    Compute Z-scores on event_count and return only anomalous rows.

    Simple global Z-score:
        z = (event_count - mean) / std

    Rows with |z| >= z_threshold are flagged as anomalies.
    """
    if df.empty:
        print("No data found in symptom_by_region; skipping anomaly detection.")
        return df.iloc[0:0]

    # store symptoms as text so it fits in a TEXT column
    df["symptoms"] = df["symptoms"].astype(str)

    mean = df["event_count"].mean()
    std = df["event_count"].std(ddof=0)

    if std == 0 or pd.isna(std):
        print("Standard deviation is zero; cannot compute anomalies.")
        return df.iloc[0:0]

    df["z_score"] = (df["event_count"] - mean) / std
    anomalies = df[df["z_score"].abs() >= z_threshold].copy()
    anomalies["detected_at"] = datetime.now(timezone.utc)

    print(f"Overall mean={mean:.3f}, std={std:.3f}")
    print(f"Detected {len(anomalies)} anomalies with |z| >= {z_threshold}")
    return anomalies


def write_anomalies(anomalies: pd.DataFrame, engine):
    """
    Write anomalies into the `anomalies` table.

    Schema:
      id                  SERIAL PRIMARY KEY
      region              TEXT
      symptoms            TEXT
      event_count         INTEGER
      avg_severity_score  DOUBLE PRECISION
      last_updated        TIMESTAMP
      z_score             DOUBLE PRECISION
      detected_at         TIMESTAMP
    """
    if anomalies.empty:
        print("No anomalies to write.")
        return

    with engine.begin() as conn:
        # Create table if it does not exist
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS anomalies (
                    id SERIAL PRIMARY KEY,
                    region TEXT,
                    symptoms TEXT,
                    event_count INTEGER,
                    avg_severity_score DOUBLE PRECISION,
                    last_updated TIMESTAMP,
                    z_score DOUBLE PRECISION,
                    detected_at TIMESTAMP
                );
                """
            )
        )

        # Prepare rows for insert
        records = anomalies[
            [
                "region",
                "symptoms",
                "event_count",
                "avg_severity_score",
                "last_updated",
                "z_score",
                "detected_at",
            ]
        ].to_dict(orient="records")

        conn.execute(
            text(
                """
                INSERT INTO anomalies (
                    region,
                    symptoms,
                    event_count,
                    avg_severity_score,
                    last_updated,
                    z_score,
                    detected_at
                )
                VALUES (
                    :region,
                    :symptoms,
                    :event_count,
                    :avg_severity_score,
                    :last_updated,
                    :z_score,
                    :detected_at
                );
                """
            ),
            records,
        )

    print(f"Wrote {len(anomalies)} anomalies to table 'anomalies'.")


# Entry point

def main():
    print("=== Phase 3: Anomaly Detection (symptom_by_region) ===")
    engine = get_engine()

    df = fetch_symptom_by_region(engine)
    print(f"Loaded {len(df)} rows from symptom_by_region.")

    anomalies = compute_anomalies(df, z_threshold=2.5)
    write_anomalies(anomalies, engine)

    print("=== Anomaly detection complete ===")


if __name__ == "__main__":
    main()
