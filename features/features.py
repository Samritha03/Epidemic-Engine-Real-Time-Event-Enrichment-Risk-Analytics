"""
Features Service Orchestrator (Phase 3)

Runs inside the `features` pod and coordinates:

- Category A1: Basic Real-Time Alerting      (category_a/basic_alerting.py)
- Category A2: Advanced Real-Time Alerting   (category_a/advanced_alerting.py)
- Category B1: Anomaly Detection             (category_b/anomaly_detection.py)
- Category B2: Outbreak Prediction           (category_b/outbreak_prediction.py)

All features share the same Postgres database (the Postgres pod in OpenShift)
and (optionally) send alerts to Slack via ALERT_WEBHOOK_URL.
"""

import os
import time
import threading

# Because this file lives in /app/features, we can import sibling packages
# directly as `category_a.*` and `category_b.*`.
from category_a.basic_alerting import run_basic_alerting                 # A1
from category_a.advanced_alerting import main as run_advanced_alerting   # A2
from category_b.anomaly_detection import main as run_anomaly_once        # B1
from category_b.outbreak_prediction import main as run_outbreak_once     # B2


# ---------------------------------------------
# Wrapper loops for Category B (B1/B2 run once)
# ---------------------------------------------

def anomaly_loop(interval_seconds: int = 300):
    """
    Periodically run anomaly detection (Category B1).

    interval_seconds = how often to re-run (default 5 minutes).
    """
    print(f"[features-orchestrator] Starting anomaly loop every {interval_seconds} seconds")
    while True:
        try:
            run_anomaly_once()
        except Exception as e:
            print(f"[features-orchestrator] Anomaly detection failed: {e}", flush=True)
        time.sleep(interval_seconds)


def outbreak_loop(interval_seconds: int = 600):
    """
    Periodically run outbreak prediction (Category B2).

    interval_seconds = how often to re-run (default 10 minutes).
    """
    print(f"[features-orchestrator] Starting outbreak loop every {interval_seconds} seconds")
    while True:
        try:
            run_outbreak_once()
        except Exception as e:
            print(f"[features-orchestrator] Outbreak prediction failed: {e}", flush=True)
        time.sleep(interval_seconds)


# ---------------------------------------------
# Main entrypoint for the `features` pod
# ---------------------------------------------

def main():
    print("======================================")
    print(" Starting Features Service Orchestrator (pod: features)")
    print(" Categories: A1 (basic), A2 (advanced), B1 (anomaly), B2 (outbreak)")
    print("======================================")

    # Ensure DB env vars exist.
    # In OpenShift, these will be set by the Deployment yaml.
    # Here we provide safe defaults for local testing.
    os.environ.setdefault("DB_HOST", "postgres")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", "epidemic")
    os.environ.setdefault("DB_USER", "ds551")
    os.environ.setdefault("DB_PASSWORD", "ds551pw")
    os.environ.setdefault("ALERT_WEBHOOK_URL", "https://hooks.slack.com/services/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")

    threads = []

    # --- Category A1: Basic alerting ---
    t_basic = threading.Thread(
        target=run_basic_alerting,
        kwargs={"poll_interval_seconds": 60},
        daemon=True,
        name="basic-alerting-thread",
    )
    threads.append(t_basic)

    # --- Category A2: Advanced alerting ---
    t_advanced = threading.Thread(
        target=run_advanced_alerting,
        daemon=True,
        name="advanced-alerting-thread",
    )
    threads.append(t_advanced)

    # --- Category B1: Anomaly detection (periodic) ---
    t_anomaly = threading.Thread(
        target=anomaly_loop,
        kwargs={"interval_seconds": 300},  # every 5 minutes
        daemon=True,
        name="anomaly-loop-thread",
    )
    threads.append(t_anomaly)

    # --- Category B2: Outbreak prediction (periodic) ---
    t_outbreak = threading.Thread(
        target=outbreak_loop,
        kwargs={"interval_seconds": 600},  # every 10 minutes
        daemon=True,
        name="outbreak-loop-thread",
    )
    threads.append(t_outbreak)

    # Start all feature threads
    for t in threads:
        print(f"[features-orchestrator] Starting thread: {t.name}")
        t.start()

    print("[features-orchestrator] All feature threads started. Running forever.")

    # Keep the main thread alive so the pod doesn't exit.
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
