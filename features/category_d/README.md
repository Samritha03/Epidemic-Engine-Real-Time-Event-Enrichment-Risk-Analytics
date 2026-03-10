# Testing & Validation (Category D)

## Overview

We implemented comprehensive testing to validate the correctness, robustness, and reliability of the epidemic analytics pipeline.
Tests focus on **data quality validation logic**, **metric aggregation**, and **Spark batch processing behavior**, ensuring issues are detected early before affecting downstream analytics or dashboards.

---

## Test Scope

### 1. Data Quality Validation (Unit Tests)

We test individual validation rules to ensure incorrect data is detected accurately:

* Null or missing fields (e.g., region, severity)
* Out-of-range values (e.g., temperature bounds)
* Invalid categorical values
* Correct flagging of failed records

**Files:**

```
tests/test_dq_utils.py
```

---

### 2. Data Quality Metrics Aggregation (Integration Tests)

We verify that row-level validation results are correctly aggregated into monitoring metrics:

* Total records processed
* Number of failures per rule
* Rows with at least one failure
* Overall DQ failure count

These metrics directly feed the `data_quality_metrics` table used by Grafana dashboards.

**Files:**

```
tests/test_dq_job.py
```

---

### 3. End-to-End Spark Batch Execution

Tests ensure Spark can:

* Initialize correctly in local mode
* Process a micro-batch of input data
* Execute validation logic via `foreachBatch`
* Produce deterministic metrics for storage and visualization

This validates that production Spark streaming logic behaves correctly under test conditions.

---

## How to Run Tests

### Prerequisites

* Python 3.10+
* Java 8 or 11
* PySpark installed
* No running Spark applications on the same machine

### Run All Tests

```bash
pytest -v
```

### Terminal Ouput
<img width="1031" height="168" alt="Screenshot 2025-12-15 at 1 08 11 AM" src="https://github.com/user-attachments/assets/d5243522-080d-4c69-b403-1abd9971afc8" />

---

## Spark Configuration for Local Testing

Spark may fail to bind to a network interface on some systems (especially macOS or VPN environments).
To ensure reliable test execution, we explicitly bind Spark to localhost in the test configuration.

**Applied in `tests/conftest.py`:**

```python
spark.driver.bindAddress = 127.0.0.1
spark.driver.host = 127.0.0.1
SPARK_LOCAL_IP = 127.0.0.1
```

This guarantees consistent Spark driver startup during testing.

---

## Why This Testing Matters

* Prevents silent data corruption from entering analytics tables
* Ensures Grafana dashboards reflect trustworthy metrics
* Validates streaming logic without requiring a live Kafka cluster
* Demonstrates production-ready engineering practices

---

## Category Mapping

✔ **Category D – Comprehensive Testing**

This testing framework validates both **functional correctness** and **system reliability** across Spark, data quality monitoring, and database integration.

