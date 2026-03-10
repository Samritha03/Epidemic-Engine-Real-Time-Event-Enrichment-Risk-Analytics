## Epidemic Engine: Real-Time Event Enrichment & Risk Analytics

### Project Overview

This repository implements a small “epidemic risk engine” running end-to-end on OpenShift.  
The system ingests synthetic public-health events in real time, cleans and enriches them with NiFi,
computes rolling features with Spark, and then uses those features to drive real-time alerts,
outbreak anomaly detection, and interactive visualization.

### Phase 1 – Real-Time Data Ingestion
- Kafka producers stream symptom, clinic, and environmental events into a shared raw topic.  
- NiFi consumes this topic, reads event_type, and routes events into three branches.  
- Each branch cleans/enriches its records with UpdateRecord and applies a standard schema.  
- Cleaned events are published to type-specific Kafka topics.  
- A copy of each stream is archived to disk for debugging.
  ![Nifi](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Nifi.png)

### Phase 2 – Analytics & Storage
- Spark jobs read from the cleaned, type-specific Kafka topics produced in Phase 1. 
- They compute rolling counts and regional aggregates for each event type.  
- Short-term vs. long-term baselines are derived for outbreak-style monitoring.  
- The computed features are written into structured tables in PostgreSQL. 
- PostgreSQL serves as the single source of truth for all downstream alerting and visualization in Phase 3.
![Analytics](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Analytics.png)

### Phase 3 – Integration + Advanced Features
Phase 3 focuses on closing the loop from streaming analytics to operational insight.
All features in this phase consume the structured feature tables produced in Phase 2 and expose them through alerting logic, dashboards, and advanced analysis.

**Category A – Alerting**

- **Basic Alerting**
  - Threshold-based alerts were implemented on rolling symptom counts and anomaly scores.
  - Alerts trigger when predefined limits (e.g., high symptom volume or anomaly z-score) are exceeded.
  - These alerts provide immediate feedback on potential outbreak signals.
- **Advanced Alerting**
  - Multi-metric alert rules combine anomaly strength, event volume, and data quality indicators.
  - Alerts are designed to reduce noise by focusing on sustained deviations rather than single spikes.
  - This approach improves alert reliability in a streaming environment.
![Slack alerts](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Slack%20Alerts.png)

**Category B – ML / Analytics**

- **Anomaly Detection**
  - Statistical anomaly detection is performed using z-score–based methods on regional symptom counts.
  - Detected anomalies are stored in the anomalies table with severity scores and timestamps.
  - This enables historical tracking of abnormal outbreak behavior.
  ![Anomaly](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Anomaly.png)
- **Outbreak Prediction**
  - A regression-based outbreak prediction model was trained using features from temporal_patterns.
  - The model predicts future event counts based on time-of-day, day-of-week, and population signals.
  - Prediction results and evaluation metrics are stored in the outbreak_predictions table for monitoring.
  ![Outbreak](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Outbreak.png)

**Category C – Visualization**

- **Jupyter Notebook**
  - The notebook implements 7 visualizations, that sit on top of the database tables created.
  - The notebook is deployed and run inside the shared Jupyter pod in our OpenShift project.
  ![Category C](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Visualisation%206.png)
  ![Category C](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Visualisation%207.png)
- **Grafana Dashboard**
  - Built directly on PostgreSQL to provide real-time observability:
    - Average anomaly strength over time
    - Top anomalous regions
    - Data quality failures over time
    - Model performance metrics (RMSE & MAE trends)
  - These dashboards allow both operational monitoring and analytical exploration of outbreak behavior.

**Category D – Testing / Data Quality Monitoring**

- **Comprehensive Testing**
  - Unit tests validate data quality rules, aggregation logic, and metric computation.
  - Spark-based tests ensure correctness of transformations independent of live streams.
  - End-to-end validation confirms correctness from Kafka ingestion through Grafana visualization.
- **Data Quality Monitoring**
  - Continuous data quality checks run inside Spark Structured Streaming micro-batches.
  - Metrics track null values, invalid ranges, and schema violations.
  - Results are persisted to PostgreSQL and visualized in Grafana for proactive monitoring. 
  
  <img width="1031" height="168" alt="Screenshot 2025-12-15 at 1 08 11 AM" src="https://github.com/user-attachments/assets/d5243522-080d-4c69-b403-1abd9971afc8" />

**Extra Credit – Advanced Enhancements**

- **ML Model Comparison**
  - As an extra credit feature, multiple lightweight ML models were implemented and compared for outbreak prediction:
    - Baseline Model: Rolling average of historical event counts
    - Linear Regression: Interpretable regression using temporal and population features
    - Gradient Boosting / Random Forest: Non-linear model capturing complex outbreak patterns
  - All models were evaluated using:
    - RMSE (Root Mean Squared Error)
    - MAE (Mean Absolute Error)
  - Results were written to PostgreSQL and visualized in Grafana, enabling continuous comparison across runs.

- **Grafana-Based Model Monitoring**
  - Grafana dashboards were built directly on PostgreSQL to provide real-time observability:
      - Average anomaly strength over time
      - Data quality failures over time
      - Model performance metrics (RMSE & MAE trends)
  - Model evaluation was treated as an operational concern rather than a one-time offline step:
  ![Grafana](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Grafana1.png)
  ![Grafana](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Grafana2.png)
  ![Grafana](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Grafana3.png)


### Architecture

Our Epidemic Engine follows a streaming, microservice-style architecture built on OpenShift:

- **Event Generators → Kafka (Raw Topic)**  
  Synthetic health events (symptom reports, clinic visits, environmental conditions) are produced continuously and sent to a shared raw Kafka topic (`ds551-f25.teamXX.raw`).

- **NiFi (Phase 1 – Routing & Enrichment)**  
  NiFi consumes the raw topic, inspects `event_type`, and routes events into three branches: `symptom_report`, `clinic_visit`, and `environmental_conditions`. Each branch enriches records with `team_id`, `processing_timestamp`, and `event_source`, then publishes them to three typed Kafka topics.

- **Spark + Database (Phase 2 – Feature Store)**  
  Spark jobs read from the typed Kafka topics, compute rolling statistics and regional features, and persist the results into a database (e.g., PostgreSQL) deployed in our OpenShift namespace with persistent storage.

- **Epidemic Features Service + Jupyter (Phase 3 – Alerts & Visualization)**  
  A service layer queries the database to generate alerts and anomaly signals, while a Jupyter notebook connects to the same database for interactive exploration and visualization of regions, trends, and alerts.

- At a high level, the **data flows** as:

  `Event Generators → Kafka (raw) → NiFi → Kafka (typed) → Spark → Postgres (Database) → Features, Juputer & Grafana (Alerts & Notebooks)`

  See `docs/architecture.md` for detailed architecture documentation.

  This is our Openshift Workflow:
  ![Topology](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Topology.png)


## Quick Start

### Prerequisites

**Required Tools:**
* OpenShift CLI (`oc`) version 4.x+ installed ([install guide](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html))
* Access to the `ds551-2025fall-fd672e` namespace on the course OpenShift cluster

**Required Access:**
* OpenShift cluster credentials: `https://api.ocp1.prod.datacom.cloud:6443`
* Shared Kafka cluster: `kafka-cluster-kafka-bootstrap:9092` (in shared namespace)
* Slack webhook URL for `#team-07-alerts` channel

**Container Images:**
* Spark: `docker.io/shraav13/spark-symptom-team07:latest`
* Features: `docker.io/samritha03/features-team07:latest`
* PostgreSQL: Standard PostgreSQL 16 image

**Local Development (Optional):**
* Docker or Podman (for building custom images)
* Java 11+ (for Spark development)
* Python 3.8+ (for features development)

### Deployment Steps

#### 1. Login to OpenShift
```bash
# Login to the cluster
oc login https://api.ocp1.prod.datacom.cloud:6443 --token=<your-token>

# Switch to team namespace
oc project ds551-2025fall-fd672e

# Verify login
oc whoami
oc get pods
```

#### 2. Deploy PostgreSQL Database
```bash
# Deploy PostgreSQL with persistent storage
oc apply -f k8s/postgres-deployment.yaml

# Wait for PostgreSQL to be ready (may take 1-2 minutes)
oc wait --for=condition=ready pod -l app=postgres --timeout=300s

# Initialize database schema
oc rsh deployment/postgres
psql -U ds551 -d epidemic -f /scripts/init-schema.sql
\q
exit

# Verify database tables exist
oc exec -it deployment/postgres -- psql -U ds551 -d epidemic -c "\dt"
```

Expected tables:
- `symptom_by_region` (Analytic 1)
- `severity_distribution` (Analytic 2)
- `temporal_patterns` (Analytic 3)
- `dq_metrics` (Data Quality)
- `anomalies` (Phase 3 - Anomaly Detection)
- `outbreak_predictions` (Phase 3 - Outbreak Prediction)

#### 3. Deploy NiFi (Phase 1 - Data Ingestion & Enrichment)
```bash
# Deploy NiFi instance
oc apply -f k8s/nifi-deployment.yaml

# Wait for NiFi to start (may take 2-3 minutes)
oc wait --for=condition=ready pod -l app=nifi --timeout=600s

# Get NiFi UI route
oc get route nifi -o jsonpath='{.spec.host}'
```

**Import NiFi Flow:**
1. Access NiFi UI at the route URL
2. Upload template: `nifi/team-flow.json`
3. Verify processors are configured:
   - **ConsumeKafka**: Bootstrap servers = `kafka-cluster-kafka-bootstrap:9092`, Topic = `ds551-f25.team07.raw`
   - **RouteOnAttribute**: Three branches (symptom_report, clinic_visit, environmental_conditions)
   - **UpdateRecord**: Adds `processing_timestamp`, `event_source`, `team_id: "07"`
   - **PublishKafka**: Publishes to three typed topics:
     - `ds551-f25.team07.symptom_reports`
     - `ds551-f25.team07.clinic_visits`
     - `ds551-f25.team07.environmental_conditions`
   - **PutFile**: Archives enriched data to `/team07/[event_type]/`

4. Start all process groups
5. Verify data flow in NiFi UI (check Data Provenance)

**NiFi Flow Verification:**
```bash
# Check NiFi logs for successful processing
oc logs deployment/nifi --tail=50 | grep "FlowFile"

# Verify NiFi is consuming from raw topic
oc exec -it deployment/nifi -- \
  kafka-console-consumer.sh \
  --bootstrap-server kafka-cluster-kafka-bootstrap:9092 \
  --topic ds551-f25.team07.raw \
  --from-beginning --max-messages 3
```

#### 4. Deploy Spark Analytics (Phase 2 - Real-Time Analytics)
```bash
# Create Spark service account with necessary RBAC permissions
oc apply -f k8s/spark-rbac.yaml

# Deploy Spark Structured Streaming job
oc apply -f k8s/spark-deployment.yaml

# Wait for Spark pod to be ready
oc wait --for=condition=ready pod -l app=spark-analytics --timeout=300s

# Monitor Spark startup logs
oc logs -f deployment/spark-symptom-analytics --tail=50
```

**Expected Spark Output:**
```
✅ Data Quality Monitoring - STARTED
✅ Analytic 1: Symptom Count by Region - STARTED
✅ Analytic 2: Severity Distribution - STARTED
✅ Analytic 3: Temporal Patterns - STARTED
All 3 Analytics Running Successfully!
```

**Spark Configuration:**
- **Input**: Kafka topic `ds551-f25.team07.symptom_reports`
- **Trigger Interval**: 30 seconds (micro-batches)
- **Output Mode**: Complete (full table refresh each batch)
- **Checkpoint**: `/tmp/checkpoint`
- **PostgreSQL Connection**: `postgres:5432/epidemic`

#### 5. Deploy Features Service (Phase 3 - Alerting & ML)
```bash
# Deploy the features pod
oc apply -f k8s/features-deployment.yaml

# Wait for features service to start
oc wait --for=condition=ready pod -l app=features --timeout=180s

# Verify all four threads started
oc logs deployment/features --tail=50
```

**Expected Features Output:**
```
[INFO] Starting Features Orchestrator...
[basic-alerting-thread] INFO: Starting basic alerting loop...
[advanced-alerting-thread] INFO: Starting advanced alerting loop...
[anomaly-loop-thread] INFO: Starting anomaly detection (interval: 300s)...
[outbreak-loop-thread] INFO: Starting outbreak prediction (interval: 600s)...
[INFO] All threads running. Press Ctrl+C to stop.
```

**Features Service Components:**
- **Basic Alerting** (`category_a/basic_alerting.py`): Threshold-based alerts
- **Advanced Alerting** (`category_a/advanced_alerting.py`): Multi-metric alerts with cooldown
- **Anomaly Detection** (`category_b/anomaly_detection.py`): Z-score detection every 5 min
- **Outbreak Prediction** (`category_b/outbreak_prediction.py`): ML models every 10 min

#### 6. Deploy Grafana Dashboards
```bash
# Deploy Grafana
oc apply -f k8s/grafana-deployment.yaml

# Wait for Grafana to be ready
oc wait --for=condition=ready pod -l app=grafana --timeout=300s

# Get Grafana route
oc get route grafana -o jsonpath='{.spec.host}'
echo "Grafana URL: https://$(oc get route grafana -o jsonpath='{.spec.host}')"
```

**Configure Grafana:**
1. Login with default credentials: `admin` / `admin`
2. Add PostgreSQL Data Source:
   - **Host**: `postgres.ds551-2025fall-fd672e.svc.cluster.local:5432`
   - **Database**: `epidemic`
   - **User**: `ds551`
   - **SSL Mode**: disable
3. Import dashboards from `grafana/dashboards/`:
   - `epidemic-overview.json` - Real-time symptom trends
   - `anomaly-detection.json` - Average anomaly strength & top regions
   - `data-quality.json` - Pipeline health & DQ failures
   - `model-performance.json` - RMSE/MAE trends

#### 7. Start Event Generators
```bash
# Deploy synthetic data generators
oc apply -f k8s/generators-deployment.yaml

# Verify generators are running
oc get pods -l component=generator

# Check generator logs
oc logs deployment/symptom-generator --tail=10
oc logs deployment/clinic-generator --tail=10
oc logs deployment/environmental-generator --tail=10
```

### Verification

#### System Health Check
```bash
# Check all pods are running
oc get pods

# Expected pods (STATUS = Running):
# postgres-xxx                    1/1     Running
# nifi-xxx                        1/1     Running
# spark-symptom-analytics-xxx     1/1     Running
# features-xxx                    1/1     Running
# grafana-xxx                     1/1     Running
# symptom-generator-xxx           1/1     Running
# clinic-generator-xxx            1/1     Running
# environmental-generator-xxx     1/1     Running
```

#### Phase 1 Verification (NiFi)
```bash
# Verify NiFi is processing events
oc logs deployment/nifi --tail=30 | grep "success"

# Check typed Kafka topics exist and have data
oc exec -it deployment/nifi -- \
  kafka-console-consumer.sh \
  --bootstrap-server kafka-cluster-kafka-bootstrap:9092 \
  --topic ds551-f25.team07.symptom_reports \
  --from-beginning --max-messages 3

# Verify enrichment: should see team_id, processing_timestamp, event_source
```

**Expected Output:** JSON with enriched fields:
```json
{
  "event_type": "symptom_report",
  "team_id": "07",
  "processing_timestamp": "2025-12-16 14:30:45",
  "event_source": "ds551-event-generator",
  "region": "region_123",
  "symptom": "fever",
  "severity_score": 7.5
}
```

#### Phase 2 Verification (Spark Analytics)
```bash
# Check Spark is consuming and processing
oc logs deployment/spark-symptom-analytics --tail=50 | grep "Batch"

# Connect to PostgreSQL
oc rsh deployment/postgres
psql -U ds551 -d epidemic

# Check analytics tables (wait 30s between checks due to batch processing)
SELECT COUNT(*) FROM symptom_by_region;
SELECT COUNT(*) FROM severity_distribution;
SELECT COUNT(*) FROM temporal_patterns;

# View Analytic 1 results
SELECT region, symptom, event_count, avg_severity 
FROM symptom_by_region 
ORDER BY event_count DESC 
LIMIT 5;

# View Analytic 2 results
SELECT hour_of_day, severity_level, event_count, percentage 
FROM severity_distribution 
ORDER BY hour_of_day, severity_level 
LIMIT 10;

# View Analytic 3 results
SELECT day_of_week, hour_of_day, event_count, unique_patients 
FROM temporal_patterns 
ORDER BY event_count DESC 
LIMIT 5;

# Check Data Quality metrics
SELECT total_records, null_failures, invalid_regions, timestamp 
FROM dq_metrics 
ORDER BY timestamp DESC 
LIMIT 3;

\q
exit
```

**Note on Empty Tables:** Due to Spark's `Complete` output mode with 30-second batches, tables are temporarily empty during writes. If you see `COUNT(*) = 0`, wait 30 seconds and query again.

#### Phase 3 Verification (Features Service)
```bash
# Monitor features service activity
oc logs deployment/features --tail=100 -f

# Expected log patterns:
# [basic-alerting-thread] Checking thresholds...
# [advanced-alerting-thread] Evaluating rules...
# [anomaly-loop-thread] Running anomaly detection...
# [outbreak-loop-thread] Training prediction models...

# Verify anomaly detection
oc rsh deployment/postgres
psql -U ds551 -d epidemic

SELECT COUNT(*) FROM anomalies;

SELECT region_id, anomaly_score, z_score, detected_at 
FROM anomalies 
ORDER BY detected_at DESC 
LIMIT 5;

# Verify outbreak predictions
SELECT COUNT(*) FROM outbreak_predictions;

SELECT region_id, model_name, predicted_count, rmse, mae, prediction_timestamp 
FROM outbreak_predictions 
ORDER BY prediction_timestamp DESC 
LIMIT 5;

\q
exit
```

#### Verify Slack Alerts
```bash
# Check features pod is sending alerts
oc logs deployment/features | grep -i "alert"

# Monitor #team-07-alerts Slack channel for messages like:
# 🚨 BASIC ALERT: High symptom count in region_456 (count: 523, threshold: 500)
# ⚠️ ADVANCED ALERT [HIGH]: Multi-metric anomaly detected
# 📊 ANOMALY: Z-score 3.45 detected in region_789

# Verify webhook is configured
oc get deployment features -o yaml | grep ALERT_WEBHOOK_URL
```

#### Grafana Dashboard Verification
```bash
# Access Grafana
echo "Grafana: https://$(oc get route grafana -o jsonpath='{.spec.host}')"

# Login: admin / admin

# Verify dashboards display data:
```

**Dashboard 1: Epidemic Overview**
- Real-time symptom counts by region
- Severity distribution heatmap
- Rolling 24-hour trends

**Dashboard 2: Anomaly Detection**
- Average anomaly strength over time
- Top 5 anomalous regions (current)
- Anomaly detection timeline

**Dashboard 3: Data Quality Monitor**
- Total records processed
- Data quality failure rate
- Null value tracking
- Invalid region alerts

**Dashboard 4: Model Performance**
- RMSE trends (Linear Regression, Random Forest, Gradient Boosting)
- MAE comparison across models
- Prediction accuracy over time

#### End-to-End Pipeline Test
```bash
# 1. Verify data generators → Kafka
oc logs deployment/symptom-generator --tail=5
# Should show: "Published event to ds551-f25.team07.raw"

# 2. Verify NiFi → Typed Kafka Topics
oc exec -it deployment/nifi -- \
  kafka-console-consumer.sh \
  --bootstrap-server kafka-cluster-kafka-bootstrap:9092 \
  --topic ds551-f25.team07.symptom_reports \
  --max-messages 1

# 3. Verify Spark → PostgreSQL (wait 30s for batch)
oc exec -it deployment/postgres -- \
  psql -U ds551 -d epidemic -c \
  "SELECT MAX(last_updated) as latest_batch FROM symptom_by_region;"

# 4. Verify Features → Anomalies & Predictions
oc exec -it deployment/postgres -- \
  psql -U ds551 -d epidemic -c \
  "SELECT MAX(detected_at) FROM anomalies;"

# 5. Check Grafana displays live data
# Visit Grafana dashboards and confirm charts update

# Full pipeline latency should be < 60 seconds end-to-end
```

### Common Issues & Solutions

#### NiFi Issues

**Problem:** NiFi processors showing validation errors  
**Solution:** Check processor configuration:
```bash
oc logs deployment/nifi --tail=100 | grep -i error
# Common fixes:
# - Verify Kafka bootstrap servers: kafka-cluster-kafka-bootstrap:9092
# - Ensure topic names match: ds551-f25.team07.*
# - Check JsonTreeReader/JsonRecordSetWriter are configured
```

**Problem:** UpdateRecord not enriching data  
**Solution:** Verify custom properties in UpdateRecord processor:
- `/processing_timestamp` → `"${now():format('yyyy-MM-dd HH:mm:ss')}"`
- `/event_source` → `"ds551-event-generator"`
- `/team_id` → `"07"`

#### Spark Issues

**Problem:** Spark pod crashlooping  
**Solution:** Check logs and common causes:
```bash
oc logs deployment/spark-symptom-analytics --tail=100

# Common issues:
# - Kafka topic not found → Verify NiFi is publishing to symptom_reports topic
# - PostgreSQL connection refused → Check postgres pod is running
# - OOM errors → Increase memory in spark-deployment.yaml
```

**Problem:** Analytics tables show `COUNT(*) = 0`  
**Solution:** This is normal behavior with `Complete` mode:
```bash
# Wait 30 seconds (batch interval) and try again
sleep 30
oc exec -it deployment/postgres -- \
  psql -U ds551 -d epidemic -c "SELECT COUNT(*) FROM symptom_by_region;"

# If still 0, check Spark is receiving data:
oc logs deployment/spark-symptom-analytics | grep "Batch"
```

**Problem:** Data Quality metrics not appearing  
**Solution:** Verify DQ monitoring is enabled:
```bash
oc logs deployment/spark-symptom-analytics | grep "\[DQ\]"
# Should see: [DQ] Batch X: total=N, null_failures=0, invalid_regions=0
```

#### Features Service Issues

**Problem:** Features pod not starting  
**Solution:** Check environment variables and database connectivity:
```bash
oc describe pod -l app=features
oc logs deployment/features --tail=50

# Verify required env vars:
oc set env deployment/features --list | grep -E "POSTGRES|ALERT_WEBHOOK"
```

**Problem:** No Slack alerts received  
**Solution:** Test webhook and check logs:
```bash
# Verify webhook URL is set
oc get deployment features -o yaml | grep ALERT_WEBHOOK_URL

# Check for alert triggers in logs
oc logs deployment/features | grep -i "alert triggered"

# Test webhook manually from features pod
oc exec -it deployment/features -- python3 -c "
import requests
webhook_url = 'YOUR_WEBHOOK_URL'
requests.post(webhook_url, json={'text': 'Test alert from features pod'})
"
```

**Problem:** Anomaly detection or prediction tables empty  
**Solution:** These run on intervals (5min/10min), check timing:
```bash
# Anomaly detection runs every 300 seconds (5 min)
# Outbreak prediction runs every 600 seconds (10 min)

# Check last run time in logs
oc logs deployment/features | grep -E "anomaly-loop|outbreak-loop" | tail -20

# Wait for next cycle and verify
watch -n 10 "oc exec -it deployment/postgres -- \
  psql -U ds551 -d epidemic -c 'SELECT COUNT(*) FROM anomalies;'"
```

#### Grafana Issues

**Problem:** Grafana shows "No Data"  
**Solution:** Verify PostgreSQL data source:
```bash
# In Grafana UI:
# Settings → Data Sources → PostgreSQL
# Click "Test" button → Should show "Database Connection OK"

# If failing, check connection details:
# Host: postgres.ds551-2025fall-fd672e.svc.cluster.local:5432
# Database: epidemic
# User: ds551

# Verify tables have data from psql
```

**Problem:** Dashboards not importing  
**Solution:** Check JSON format and panel queries:
- Ensure JSON files are valid
- Verify table names match PostgreSQL schema
- Check time field is set correctly in panel queries

### Stopping the System
```bash
# Option 1: Scale down (preserves configuration and data)
oc scale deployment --all --replicas=0

# Option 2: Delete all deployments (removes everything)
oc delete -f k8s/ --recursive

# Option 3: Stop specific components
oc scale deployment nifi --replicas=0
oc scale deployment spark-symptom-analytics --replicas=0
oc scale deployment features --replicas=0

# Keep PostgreSQL running for data analysis
oc scale deployment postgres --replicas=1
```

### Restarting the System
```bash
# Scale everything back up
oc scale deployment --all --replicas=1

# Or restart specific components
oc scale deployment nifi spark-symptom-analytics features --replicas=1

# Verify all pods come back up
oc get pods -w
```




