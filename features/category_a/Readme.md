## Category A – Real-Time Alerting (Basic + Advanced)

This feature category provides a live alerting layer on top of the Phase 2 Spark analytics tables. It continuously watches the `symptom_by_region` and `severity_distribution` tables in Postgres and sends alerts to Slack when activity crosses configured thresholds.

Implemented **both**:
- **A1 – Basic Real-Time Alerting** (`features/category_a/basic_alerting.py`)
- **A2 – Advanced Real-Time Alerting** (`features/category_a/advanced_alerting.py`, `features/category_a/advanced_alert_config.json`)

Both are orchestrated by `features.py` and run inside the `features` pod.

##
### Data Flow

**End-to-end pipeline:** `Event Generator → NiFi → Kafka → Spark Symptom Analytics → Postgres (symptom_by_region, severity_distribution) → Features Pod (Category A) → Slack alerts`
- The Spark analytics job aggregates raw events into:
  - `symptom_by_region`: 5-minute rolling counts of symptom events by region.
  - `severity_distribution`: share of severe vs non-severe cases by region / time window.
- The **features pod** connects to the same Postgres database and polls these tables on a schedule.
- When thresholds are exceeded, the alerting code posts messages to a **Slack Incoming Webhook**.

##
### Basic Real-Time Alerting (A1)

**Goal:** Simple alerts when core metrics cross fixed thresholds.

**What it monitors:** Currently our basic alerts cover two main checks:
- **High visit volume per region**
   - Computes total `event_count` per region over the last 5 minutes.
   - Triggers if any region exceeds a fixed threshold (e.g. **500 events / 5 min**).
- **High severe case share**
   - Uses recent `severity_distribution` data.
   - Triggers if the fraction of severe cases exceeds a configured threshold (e.g. **40%**).

**Alert format:** When a basic alert fires, it prints to logs and sends a Slack message with:
- Alert type (e.g., *High visit volume detected*).
- Timestamp (UTC).
- Threshold values.
- A short list of regions and their current counts / percentages.

**Schedule**
- `features.py` starts `run_basic_alerting(poll_interval_seconds=60)` in its own thread.
- The basic alert loop runs **every minute** and always uses the latest data already written by Spark.

##
### Advanced Real-Time Alerting (A2)

**Goal:** A configurable, production-style alerting service with severity levels and cooldowns.

**Key capabilities:**
- **Z-score–based anomaly scoring:** For each region, the advanced alerting job compares the current 5-minute activity against recent history using Z-scores. Larger |z| means more unusual activity, and those z-values drive the severity labels (e.g., LOW for mild deviation, MEDIUM for moderate, HIGH for extreme spikes)
- **Severity levels:** The advanced alerting code computes how unusual the current metrics are (e.g., based on deviation from recent averages) and maps them to labeled severities such as: `LOW`, `MEDIUM`, `HIGH`. 
- **Cooldown / suppression:**
   - To avoid spamming Slack, each alert key has a cooldown window (e.g., 10 minutes).
   - If the same `MEDIUM` or `HIGH` condition repeats during cooldown, the log shows a suppression message: `"[advanced-alert] HIGH alert suppressed (cooldown ... remaining)"`
- **Config-driven behavior:** The JSON file `advanced_alert_config.json` controls:
   - Metric names and thresholds.
   - Which severity levels to emit.
   - Cooldown duration per alert type.
   - Optional routing info for different Slack channels (if needed).

   This allows changes to thresholds or severity logic without editing Python source.

**Schedule**
- `features.py` starts `advanced_alerting.main()` in its own thread.
- `advanced_alerting` contains its own internal polling loop (similar cadence to basic alerting).

##
### Slack Integration

Both A1 and A2 send alerts to Slack via a **single webhook URL**.

- The webhook is passed to the container as an environment variable:
  ```yaml
  name: ALERT_WEBHOOK_URL
  value: "https://hooks.slack.com/services/XXX/YYY/ZZZ"```
- Inside both alerting modules, we read:
  ```webhook_url = os.environ.get("ALERT_WEBHOOK_URL")```
- If ALERT_WEBHOOK_URL is not set, the code falls back to logging alerts to stdout only (no Slack messages).

##
### How It Runs in OpenShift

**Pod:** features

**Image:** ```samritha03/features-team07:latest``` (built from features/Dockerfile.features)

**Entrypoint:** features.py

**At runtime:** The features Deployment injects database credentials and the Slack webhook
```features.py``` starts threads:
- basic-alerting-thread (A1)
- advanced-alerting-thread (A2)

**Logs from Category A are visible via (features pod):** ```oc logs deployment/features```

**Logs from Category A (Slack channel):**
![Category A – Slack alerts](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Slack%20Alerts.png)

