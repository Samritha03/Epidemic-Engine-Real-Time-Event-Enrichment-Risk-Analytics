
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from features.category_d.dq_job import apply_validation, compute_metrics


def test_apply_validation_flags_out_of_range_temperature(spark):
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

    validated = apply_validation(df, rules).collect()[0]

    assert validated["temperature_range_fail"] == 1
    assert validated["dq_fail"] >= 1
    