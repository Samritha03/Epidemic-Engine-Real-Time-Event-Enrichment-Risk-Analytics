# features/data_quality/dq_utils.py

import os
import json
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    when,
    lit,
    count,
    sum as spark_sum,
    current_timestamp,
    isnan,
    isnull,
)

DB_URL = os.getenv("DB_URL", "jdbc:postgresql://postgres:5432/epidemic")
DB_USER = os.getenv("DB_USER", "epidemic_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "epidemic_password")
DQ_METRICS_TABLE = os.getenv("DB_DQ_TABLE", "data_quality_metrics")

RULES_PATH = os.getenv(
    "DQ_RULES_PATH",
    str(Path(__file__).resolve().parent / "dq_rules.json"),
)


def load_rules(path: str = RULES_PATH) -> dict:
    """Load data quality rules from JSON."""
    with open(path, "r") as f:
        return json.load(f)


def apply_validation(df: DataFrame, rules: dict) -> DataFrame:
    """
    Apply validation rules to the DataFrame.
    Adds *_fail columns and a combined dq_fail column.
    """
    validated_df = df

    # Null checks on core fields
    required_cols = ["temperature", "humidity", "symptom_count", "region"]
    for c in required_cols:
        if c in validated_df.columns:
            validated_df = validated_df.withColumn(
                f"{c}_null_fail",
                when(isnull(col(c)) | isnan(col(c)), lit(1)).otherwise(0),
            )

    # Temperature range
    if "temperature" in rules and "temperature" in validated_df.columns:
        r = rules["temperature"]
        min_v = r.get("min", float("-inf"))
        max_v = r.get("max", float("inf"))
        validated_df = validated_df.withColumn(
            "temperature_range_fail",
            when((col("temperature") < min_v) | (col("temperature") > max_v), lit(1)).otherwise(0),
        )

    # Humidity range
    if "humidity" in rules and "humidity" in validated_df.columns:
        r = rules["humidity"]
        min_v = r.get("min", float("-inf"))
        max_v = r.get("max", float("inf"))
        validated_df = validated_df.withColumn(
            "humidity_range_fail",
            when((col("humidity") < min_v) | (col("humidity") > max_v), lit(1)).otherwise(0),
        )

    # Symptom count minimum
    if "symptom_count" in rules and "symptom_count" in validated_df.columns:
        r = rules["symptom_count"]
        min_v = r.get("min", float("-inf"))
        validated_df = validated_df.withColumn(
            "symptom_min_fail",
            when(col("symptom_count") < min_v, lit(1)).otherwise(0),
        )

    # Region allowed list
    if "region" in rules and "region" in validated_df.columns:
        allowed = rules["region"].get("allowed", [])
        if allowed:
            validated_df = validated_df.withColumn(
                "region_allowed_fail",
                when(~col("region").isin(allowed), lit(1)).otherwise(0),
            )

    # Combine all *_fail columns
    fail_cols = [c for c in validated_df.columns if c.endswith("_fail")]
    if fail_cols:
        expr = None
        for c in fail_cols:
            expr = col(c) if expr is None else expr + col(c)
        validated_df = validated_df.withColumn("dq_fail", expr)
    else:
        validated_df = validated_df.withColumn("dq_fail", lit(0))

    return validated_df


def compute_metrics(df: DataFrame) -> DataFrame:
    """
    Aggregate data quality metrics across the batch.
    """
    fail_cols = [c for c in df.columns if c.endswith("_fail")]

    agg_exprs = [count("*").alias("total_records")]
    for c in fail_cols:
        agg_exprs.append(spark_sum(col(c)).alias(c))

    agg_exprs.append(
        spark_sum(when(col("dq_fail") > 0, 1).otherwise(0)).alias("rows_with_any_failure")
    )

    metrics_df = df.select(*agg_exprs).withColumn("timestamp", current_timestamp())
    return metrics_df


def write_metrics_to_db(metrics_df: DataFrame):
    """
    Append metrics into the data_quality_metrics table.
    """
    (
        metrics_df.write.format("jdbc")
        .option("url", DB_URL)
        .option("dbtable", DQ_METRICS_TABLE)
        .option("user", DB_USER)
        .option("password", DB_PASSWORD)
        .mode("append")
        .save()
    )
