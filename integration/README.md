# End-to-End Integration 

## Objective
Show the full pipeline works:
Event Generator → NiFi → Typed Kafka Topics → Spark Analytics → PostgreSQL → Phase 3 Features

---

## A. Complete Pipeline Operation (10 pts)

### 1) NiFi: Raw → Typed Kafka Topics (Phase 1)
- **Flow export:** `nifi/team-flow.json`
- **Flow documentation:** `nifi/README.md`
- **Input topic:** `ds551-f25.team07.raw`
- **Output topics:**
  - `ds551-f25.team07.symptom_reports`
  - `ds551-f25.team07.clinic_visits`
  - `ds551-f25.team07.environmental`
- **Verification (Kafka):**
  - Consume from each typed topic and confirm:
    - correct `event_type`
    - enrichment fields exist: `team_id`, `processing_timestamp`, `event_source`

### 2) Spark: Typed Kafka → PostgreSQL Feature Tables (Phase 2)
- **Spark job code:** `spark/spark_job.py`
- **Spark documentation:** `spark/README.md`
- **Spark deployment manifests:** `k8s/spark/` (or your actual folder)
- **Database manifests:** `k8s/database/`
- **Verification (DB):**
  - Confirm tables populate (examples):
    - `event_counts`
    - `anomalies` / `anomaly_events`
    - `outbreak_predictions`
    - `temporal_patterns`
    - `data_quality_metrics`
  - Sample query:
    ```sql
    SELECT COUNT(*) FROM event_counts;
    ```

---

## B. Feature Integration (5 pts)

### Phase 3 Feature Consuming Phase 2 Outputs
At least one Phase 3 feature directly consumes the PostgreSQL feature tables produced by Spark.

**Integrated feature(s):**
1) **Grafana Dashboards**
- **Consumes:** PostgreSQL tables (feature store)
- **Evidence:** Grafana screenshots in root `README.md` (model monitoring / data quality / anomaly trends)

2) **Jupyter Notebook Visualization**
- **Consumes:** PostgreSQL tables (feature store)
- **Location:** `notebooks/analysis.ipynb` (and exported HTML/PDF if included)
- **Verification:** open notebook and run cells to query PostgreSQL and render plots

---

## Where to find evidence in this repo
- **NiFi:** `nifi/README.md`, `nifi/team-flow.json`
- **Spark:** `spark/README.md`, `spark/spark_job.py`, `spark/Dockerfile`
- **OpenShift manifests:** `k8s/database/`, `k8s/spark/`, `k8s/` (Phase 3 services)
- **Architecture:** `docs/architecture.md`
- **Dashboards evidence:** screenshots embedded in root `README.md`

