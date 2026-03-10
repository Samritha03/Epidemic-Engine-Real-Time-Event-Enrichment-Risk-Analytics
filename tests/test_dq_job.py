# tests/test_dq_job.py
import os
import sys
from features.category_d import dq_job

from pyspark.sql.types import StructType, StructField, DoubleType, IntegerType, StringType


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)



def test_apply_validation_flags_out_of_range_temperature(spark):
    # Arrange: one clearly bad record
    df = spark.createDataFrame(
        [
            {
                "temperature": 200.0,
                "humidity": 50.0,
                "symptom_count": 10,
                "region": "NE",
            }
        ]
    )

    rules = {
        "temperature": {"min": -50, "max": 60},
        "humidity": {"min": 0, "max": 100},
        "symptom_count": {"min": 0},
        "region": {"allowed": ["NE", "NW"]},
    }

    # Act
    validated = dq_job.apply_validation(df, rules).collect()[0]

    # Assert
    assert validated["temperature_range_fail"] == 1
    assert validated["dq_fail"] >= 1



def test_apply_validation_null_fields(spark):
    # Arrange: record with null humidity and null region
    data = [
        {
            "temperature": 20.0,
            "humidity": None,
            "symptom_count": 5,
            "region": None,
        }
    ]

    # Explicit schema so Spark doesn't have to infer columns that are all null
    schema = StructType([
        StructField("temperature", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("symptom_count", IntegerType(), True),
        StructField("region", StringType(), True),
    ])

    df = spark.createDataFrame(data=data, schema=schema)

    rules = {
        "temperature": {"min": -50, "max": 60},
        "humidity": {"min": 0, "max": 100},
        "symptom_count": {"min": 0},
        "region": {"allowed": ["NE", "NW"]},
    }

    validated = dq_job.apply_validation(df, rules).collect()[0]

    assert validated["humidity_null_fail"] == 1
    assert validated["region_null_fail"] == 1
    assert validated["dq_fail"] >= 2


def test_compute_metrics_counts_failures(spark):
    # Arrange: two records, one clean, one with bad values
    df = spark.createDataFrame(
        [
            {
                "temperature": 20.0,
                "humidity": 50.0,
                "symptom_count": 5,
                "region": "NE",
            },
            {
                "temperature": 200.0,
                "humidity": -10.0,
                "symptom_count": -1,
                "region": "X",
            },
        ]
    )

    rules = {
        "temperature": {"min": -50, "max": 60},
        "humidity": {"min": 0, "max": 100},
        "symptom_count": {"min": 0},
        "region": {"allowed": ["NE", "NW"]},
    }

    validated = dq_job.apply_validation(df, rules)
    metrics_df = dq_job.compute_metrics(validated)
    metrics = metrics_df.collect()[0]

    # We had 2 rows total
    assert metrics["total_records"] == 2

    # Second row violates multiple rules; all failure counts should be >= 1
    assert metrics["temperature_range_fail"] >= 1
    assert metrics["humidity_range_fail"] >= 1
    assert metrics["symptom_min_fail"] >= 1
    assert metrics["region_allowed_fail"] >= 1
    assert metrics["rows_with_any_failure"] >= 1

    # Timestamp should not be null
    assert metrics["timestamp"] is not None
