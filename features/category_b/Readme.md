## Category B – ML / Analytics 

Implemented **both**:
- **B1 – Anomaly Detection** (`features/category_b/anomaly_detection.py`)
- **B2 – Outbreak Prediction Model** (`features/category_b/outbreak_prediction.py`)

Category B adds analytics on top of the Phase 2 Spark outputs stored in Postgres. Both scripts run inside the shared `features` pod and write their results back into
the same `epidemic` database.

##
### Data Sources and Output Tables

All queries go against the Postgres database created in Phases 1–2.
- **Input tables**
  - `symptom_by_region` – Aggregated symptom event counts per `(region, time bucket)`. Used by anomaly_detection.py
  - `temporal_patterns` – Time series aggregates combining symptoms and environment over fixed windows. Used by outbreak_prediction.py
- **Output tables**
  - `anomalies` – One row per detected anomaly. Contains region, timestamp, metric, z-score, and deviation info.
  - `outbreak_predictions` – One row per model prediction. Contains run_id, timestamp, region (if applicable), predicted value, and error metrics.

##
### Anomaly Detection (B1)

**Goal:** Flag statistically unusual spikes in symptom activity by region, based on the aggregated counts in `symptom_by_region`.

**Method:** 
- Load recent rows from symptom_by_region.
- For each (`region`, `time_bucket`):
  - Compute z-scores for the event count relative to the overall mean and standard deviation of the recent window.
  - Mark a row as anomalous when |z| >= 2.5 (configurable threshold in code).
- For each anomaly, insert a row into the anomalies table with:
  - timestamp / time bucket
  - region
  - event_count
  - mean, std, and z-score used for the decision

This is a statistical anomaly detector (not a ML model) based on a z-score rule over the rolling distribution of counts.

**Runtime behavior:** When run directly (locally), anomaly_detection.py performs one pass and exits. In OpenShift, features.py wraps it in a loop:
```python
# in features.py
def anomaly_loop(interval_seconds=300):
    while True:
        run_anomaly_once()     # calls anomaly_detection.main()
        time.sleep(interval_seconds)
```
The features pod runs this loop every 5 minutes, continually appending new anomalies to the anomalies table.

##
### Outbreak Prediction Model (B2)

**Goal:** Train a small ML model that predicts future epidemic activity based on recent temporal patterns, and store the predictions for downstream use.

**ML Model:**
- *Model type*: `RandomForestRegressor` (from `sklearn.ensemble`)
- *Task:* Regression – predict a future activity metric (e.g., next time-window event count) from engineered features.

**Method:** 
- Load rows from temporal_patterns into a Pandas DataFrame.
- Perform basic feature engineering (e.g., recent event counts, severe share, environmental statistics, and simple lagged features from recent windows).
- Split the data into train / test sets.
- Train a Random Forest regression model on the training set.
- Evaluate on the test split and log metrics such as: **RMSE, MAE**.
- For the most recent rows, generate predictions and write them to outbreak_predictions, tagged with a unique run_id and timestamp.

**Runtime behavior:** When run directly, outbreak_prediction.py executes one training + predict cycle and exits. In OpenShift, features.py runs it in a periodic loop:
```python
# in features.py
def outbreak_loop(interval_seconds=600):
    while True:
        run_outbreak_once()    # calls outbreak_prediction.main()
        time.sleep(interval_seconds)
```
The features pod triggers a new outbreak prediction run about every 10 minutes, appending new rows into outbreak_predictions.

##
### How It Runs in OpenShift

**Pod:** features

**Image:** ```samritha03/features-team07:latest``` (built from features/Dockerfile.features)

**Entrypoint:** features.py

**At runtime:** 
- The Deployment injects DB and Slack environment variables: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `features.py` starts threads:
  - anomaly-loop-thread (Category B1)
  - outbreak-loop-thread (Category B2)
- Category B behavior is visible via:
```bash
oc logs deployment/features | grep -i "Anomaly"
oc logs deployment/features | grep -i "Outbreak"
```
- And in Postgres:
```sql
SELECT COUNT(*) FROM anomalies;
SELECT COUNT(*) FROM outbreak_predictions;
```

**Logs from Category B are visible via (features pod):** ```oc logs deployment/features```

**Logs from Category B (Locally):**
![Category B – Anomaly](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Anomaly.png)

![Category B – Outbreak](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Outbreak.png)

