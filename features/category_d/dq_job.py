# features/category_d/dq_job.py

import os
import json
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
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

# -------------------------------------------------------------------
# Configuration (override via environment variables in OpenShift)
# -------------------------------------------------------------------


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "epidemic")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ds551")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ds551pw")

JDBC_URL = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
# Table that contains your events (adjust if your table name differs)
EVENTS_TABLE = os.getenv("DB_EVENTS_TABLE", "events")

# Table to store DQ metrics
DQ_METRICS_TABLE = os.getenv("DB_DQ_TABLE", "data_quality_metrics")

# Path to rules JSON
RULES_PATH = os.getenv(
    "DQ_RULES_PATH",
    str(Path(__file__).resolve().parent / "dq_rules.json"),
)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def get_spark_session(app_name: str = "DataQualityJob") -> SparkSession:
    """
    Create a SparkSession. The postgres JDBC driver should be available
    in the image or provided via --jars in spark-submit.
    """
    spark = (
        SparkSession.builder.appName(app_name)
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.3")
        .getOrCreate()
    )
    return spark


def load_rules(path: str = RULES_PATH) -> dict:
    """
    Load data quality rules from a JSON file.
    """
    with open(path, "r") as f:
        return json.load(f)


def load_events_df(spark: SparkSession) -> DataFrame:
    """
    Load events from the database as a DataFrame.

    Assumes a table with at least:
      temperature, humidity, symptom_count, region
    and optionally: timestamp, id, etc.
    """
    df = (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", DQ_METRICS_TABLE)
        .option("user", POSTGRES_USER)
        .option("password", POSTGRES_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .mode("append")
        .load()
    )
    return df


def apply_validation(df: DataFrame, rules: dict) -> DataFrame:
    """
    Apply validation rules to the DataFrame.

    Adds:
      - *_null_fail columns for required fields
      - *_range_fail / *_min_fail / region_allowed_fail
      - dq_fail: sum of all individual fail flags per row
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
            when(
                (col("temperature") < min_v) | (col("temperature") > max_v),
                lit(1),
            ).otherwise(0),
        )

    # Humidity range
    if "humidity" in rules and "humidity" in validated_df.columns:
        r = rules["humidity"]
        min_v = r.get("min", float("-inf"))
        max_v = r.get("max", float("inf"))
        validated_df = validated_df.withColumn(
            "humidity_range_fail",
            when(
                (col("humidity") < min_v) | (col("humidity") > max_v),
                lit(1),
            ).otherwise(0),
        )

    # Symptom minimum
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

    # Combine all *_fail columns into dq_fail
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
    Aggregate data quality metrics over the entire DataFrame.

    Produces one-row DataFrame with:
      - total_records
      - failure counts per rule
      - rows_with_any_failure
      - timestamp
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


def write_metrics_to_db(metrics_df: DataFrame) -> None:
    """
    Append metrics into the data_quality_metrics table.
    """
    (
        metrics_df.write.format("jdbc")
        # .option("url", DB_URL)
        # .option("dbtable", DQ_METRICS_TABLE)
        # .option("user", DB_USER)
        # .option("password", DB_PASSWORD)
        # .mode("append")
        # .save()
        .option("url", JDBC_URL)
        .option("dbtable", DQ_METRICS_TABLE)
        .option("user", POSTGRES_USER)
        .option("password", POSTGRES_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .mode("append")
        .save()
    )


def run_dq_for_df(df: DataFrame) -> DataFrame:
    """
    Helper to be called from spark_job.py.

    Example usage inside your analytics job:
        from features.category_d.dq_job import run_dq_for_df
        dq_metrics = run_dq_for_df(events_df)
    """
    rules = load_rules()
    validated = apply_validation(df, rules)
    metrics_df = compute_metrics(validated)
    return metrics_df


# -------------------------------------------------------------------
# Optional: standalone execution (batch mode)
# -------------------------------------------------------------------

def main():
    spark = get_spark_session()

    print("[DQ] Loading rules from:", RULES_PATH)
    rules = load_rules()

    print("[DQ] Loading events from DB table:", EVENTS_TABLE)
    events_df = load_events_df(spark)

    if events_df.rdd.isEmpty():
        print("[DQ] No records in events table. Exiting without writing metrics.")
        spark.stop()
        return

    print("[DQ] Applying validation rules...")
    validated_df = apply_validation(events_df, rules)

    print("[DQ] Computing metrics...")
    metrics_df = compute_metrics(validated_df)

    print("[DQ] Writing metrics to DB table:", DQ_METRICS_TABLE)
    write_metrics_to_db(metrics_df)

    print("[DQ] Data quality job finished.")
    spark.stop()

def run_dq_for_df(df: DataFrame) -> DataFrame:
    """
    Apply validation rules to a batch DataFrame and return aggregated metrics.
    This is what we call from foreachBatch(df, epochId).
    """
    validated = apply_validation(df, load_rules())
    metrics = compute_metrics(validated)
    return metrics



if __name__ == "__main__":
    main()
