# Architecture Documentation

This document describes the system architecture for **Team 07’s Epidemic Engine**, developed as part of **DS-551: Data Engineering at Scale (Fall 2025)**. The architecture demonstrates a complete, cloud-native, end-to-end streaming data platform deployed on OpenShift.

---

## System Overview

The Epidemic Engine is a real-time data platform designed to ingest, process, analyze, and visualize public-health events. Synthetic health events are continuously generated, routed and enriched using Apache NiFi, analyzed using Apache Spark, and persisted in PostgreSQL as structured feature tables. These features are then consumed by alerting services, machine learning models, dashboards, and interactive notebooks.

The system is organized into three phases, where each phase builds directly on the outputs of the previous one, ensuring full end-to-end integration.

---

## Data Flow

Data flows through the system as follows:

Event Generator → Kafka (Raw Topic)
→ NiFi (Routing & Enrichment)
→ Kafka (Typed Topics)
→ Spark Structured Streaming
→ PostgreSQL (Feature Store)
→ Phase 3 Features (Alerts, ML, Visualization, Data Quality)


---

## Components

### Phase 1: NiFi Ingestion Pipeline

The Phase 1 ingestion pipeline is responsible for consuming raw events, enriching them with metadata, and producing clean, type-specific Kafka streams.

**Approach:**
- Apache NiFi consumes events from the raw Kafka topic `ds551-f25.team07.raw`
- Events are inspected using the `event_type` field
- Records are routed into separate branches for:
  - `symptom_report`
  - `clinic_visit`
  - `environmental_conditions`
- Each event is enriched with:
  - `team_id`
  - `processing_timestamp`
  - `event_source`
- Enriched records are published to type-specific Kafka topics

**Output Kafka Topics:**
- `ds551-f25.team07.symptom_reports`
- `ds551-f25.team07.clinic_visits`
- `ds551-f25.team07.environmental`

This phase ensures downstream analytics operate on consistent and validated data streams.

---

### Phase 2: Spark Analytics & Database

Phase 2 transforms streaming events into durable analytical features using Apache Spark and PostgreSQL.

**Approach:**
- Apache Spark Structured Streaming
- 30-second micro-batches
- Consumes from Kafka topic `ds551-f25.team07.symptom_reports`

**Analytics Implemented:**

1. **Symptom Count by Region**  
   Aggregates symptom events by geographic region to identify localized outbreak patterns.  
   Stored in table: `symptom_by_region`

2. **Severity Distribution by Hour**  
   Computes hourly severity patterns to support staffing and operational planning.  
   Stored in table: `severity_distribution`

3. **Temporal Patterns**  
   Captures day-of-week and hour-of-day trends used as features for outbreak prediction.  
   Stored in table: `temporal_patterns`

4. **Data Quality Monitoring**  
   Tracks null values, invalid ranges, and schema violations in real time.  
   Stored in table: `dq_metrics`

**Database Choice: PostgreSQL 16**

**Rationale:**
- ACID compliance suitable for healthcare-style data
- Strong SQL support for analytics and dashboards
- Native Spark JDBC integration
- Persistent storage via PVC on OpenShift
- Production-ready reliability and performance

PostgreSQL acts as the central **feature store** for all downstream components.

---

### Phase 3: Advanced Features

Phase 3 consumes the structured feature tables produced in Phase 2 and exposes them through alerts, machine learning models, dashboards, and interactive analysis tools. All Phase 3 features directly depend on Phase 2 outputs, ensuring true end-to-end integration.

#### Alerting
- **Basic Alerting**
  - Threshold-based alerts on rolling symptom counts and anomaly scores
- **Advanced Alerting**
  - Multi-metric rules combining:
    - Event volume
    - Anomaly strength
    - Data quality indicators
- Alerts are delivered using Slack Webhooks

#### Machine Learning & Analytics
- **Anomaly Detection**
  - Z-score–based anomaly detection on regional symptom counts
- **Outbreak Prediction**
  - Regression-based prediction models using temporal features
- **ML Model Comparison (Extra Credit)**
  - Baseline rolling average
  - Linear regression
  - Tree-based models
  - Performance evaluated using RMSE and MAE over time

#### Visualization
- **Jupyter Notebooks**
  - Interactive exploration and advanced visualization
  - Direct SQL access to PostgreSQL feature tables
- **Grafana Dashboards**
  - Connected directly to PostgreSQL
  - Visualize:
    - Anomaly trends
    - Top anomalous regions
    - Data quality failures
    - ML model performance metrics

#### Testing & Data Quality
- Unit tests validate Spark transformations and aggregation logic
- Continuous data quality checks run within Spark streaming jobs
- Quality metrics are persisted to PostgreSQL and visualized in Grafana

---

## Technology Choices

### Database
**PostgreSQL 16**

**Why:**
- Reliable transactional guarantees
- Mature ecosystem and tooling
- Seamless integration with Spark, Grafana, and Jupyter
- Suitable for both analytics and operational workloads

### Spark Approach

**Decision:** Real-time streaming (not batch processing)

**Rationale:**

1. **Real-Time Requirements**
   - Epidemic monitoring requires near real-time insights
   - Alerts depend on timely anomaly detection

2. **Continuous Processing**
   - Data is processed as it arrives from Kafka
   - Aggregations remain continuously updated

3. **Fault Tolerance**
   - Checkpointing ensures exactly-once semantics
   - Automatic recovery from failures without data loss

4. **Native Kafka Integration**
   - Direct consumption from Kafka topics
   - Built-in offset management and backpressure handling

5. **Developer Productivity**
   - SQL-like DataFrame API
   - Clear and maintainable analytics code

---

## Deployment

All system components are deployed within the OpenShift namespace:

**`ds551-2025fall-team07`**

- Apache NiFi, Kafka, Spark, PostgreSQL, Jupyter, Grafana, and alerting services run as containerized workloads
- PostgreSQL uses persistent volumes to ensure data durability
- Internal Kubernetes services enable secure inter-component communication

---

## Diagrams

The following diagram illustrates the complete end-to-end system architecture across all three phases:
<img width="1286" height="962" alt="Untitled Diagram drawio (2)" src="https://github.com/user-attachments/assets/78bb3f44-854b-42bf-bb63-9d0f0adbbab7" />


