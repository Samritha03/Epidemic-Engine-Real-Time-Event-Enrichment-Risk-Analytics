from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, count, avg, 
    current_timestamp, to_timestamp, hour, dayofweek, when
)
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from features.category_d.dq_job import run_dq_for_df, write_metrics_to_db

import os

# Configuration from environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka-team07:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "ds551-f25.team07.symptom_reports")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "epidemic")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ds551")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ds551pw")
TEAM_ID = "07"

# Define schema for symptom_report events
symptom_schema = StructType([
    StructField("event_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("patient_id", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("gender", StringType(), True),
    StructField("region", StringType(), True),
    StructField("symptoms", StringType(), True),
    StructField("severity", StringType(), True),
    StructField("team_id", StringType(), True),
    StructField("processing_timestamp", StringType(), True),
    StructField("event_source", StringType(), True)
])

def create_postgres_connection_properties():
    """Create PostgreSQL connection properties"""
    return {
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "driver": "org.postgresql.Driver"
    }

def write_to_postgres(df, table_name, mode="append"):
    """Write DataFrame to PostgreSQL"""
    jdbc_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    properties = create_postgres_connection_properties()
    
    df.write \
        .jdbc(url=jdbc_url, table=table_name, mode=mode, properties=properties)

def main():
    # Initialize Spark Session
    spark = SparkSession.builder \
        .appName("SymptomAnalytics-Team07") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,"
                "org.postgresql:postgresql:42.5.0") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoint") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("=" * 60)
    print("Starting Symptom Analytics for Team 07")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    print(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    print("=" * 60)
    
    # Read from Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "earliest") \
        .load()
    
    # Parse JSON and extract fields
    parsed_df = kafka_df.select(
        from_json(col("value").cast("string"), symptom_schema).alias("data")
    ).select("data.*")
    
    # Convert timestamp to proper format
    parsed_df = parsed_df.withColumn(
        "event_timestamp",
        to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSS")
    )
    
    # Map severity to numeric score for analysis
    severity_df = parsed_df.withColumn(
        "severity_score",
        when(col("severity") == "mild", 1)
        .when(col("severity") == "moderate", 2)
        .when(col("severity") == "severe", 3)
        .when(col("severity") == "critical", 4)
        .otherwise(0)
    )
    # ============================================
# DATA QUALITY MONITORING (Category D Feature)
# ============================================

    # def dq_batch(df, epoch_id):
    #     print(f"[DQ] Running Data Quality for batch {epoch_id}")
    #     dq_metrics = run_dq_for_df(df)        # compute metrics
    #     write_metrics_to_db(dq_metrics)       # store metrics in DB

    # dq_query = severity_df \
    #     .writeStream \
    #     .outputMode("append") \
    #     .foreachBatch(dq_batch) \
    #     .trigger(processingTime="30 seconds") \
    #     .start()

    # print("✅ Data Quality Monitoring - STARTED")
    print("Setting up Data Quality Monitoring")

    def dq_batch(df, epoch_id):
        print(f"[DQ] Running Data Quality for batch {epoch_id}")
        dq_metrics_df = run_dq_for_df(df)   # validate + aggregate
        dq_metrics_df.show(truncate=False)  # helpful for debugging
        write_metrics_to_db(dq_metrics_df)  # write to Postgres

    dq_query = severity_df \
        .writeStream \
        .outputMode("append") \
        .foreachBatch(dq_batch) \
        .trigger(processingTime="30 seconds") \
        .start()

    print("✅ Data Quality Monitoring - STARTED")


    # ============================================
    # ANALYTIC 1: Symptom Count by Region
    # ============================================
    print("Setting up Analytic 1: Symptom Count by Region")
    
    symptom_by_region = severity_df \
        .groupBy("region", "symptoms") \
        .agg(
            count("*").alias("event_count"),
            avg("severity_score").alias("avg_severity_score")
        ) \
        .withColumn("last_updated", current_timestamp())
    
    query1 = symptom_by_region \
        .writeStream \
        .outputMode("complete") \
        .foreachBatch(lambda df, epoch_id: write_to_postgres(df, "symptom_by_region", "overwrite")) \
        .trigger(processingTime='30 seconds') \
        .start()
    
    print("✅ Analytic 1: Symptom Count by Region - STARTED")
    
    # ============================================
    # ANALYTIC 2: Severity Distribution by Hour
    # ============================================
    print("Setting up Analytic 2: Severity Distribution by Hour")
    
    severity_by_hour = severity_df \
        .withColumn("hour_of_day", hour("event_timestamp")) \
        .groupBy("severity", "hour_of_day") \
        .agg(count("*").alias("event_count")) \
        .withColumn("last_updated", current_timestamp()) \
        .withColumn("percentage", col("event_count") * 100.0)
    
    # Write Analytic 2 to PostgreSQL
    query2 = severity_by_hour \
        .writeStream \
        .outputMode("complete") \
        .foreachBatch(lambda df, epoch_id: write_to_postgres(df, "severity_distribution", "overwrite")) \
        .trigger(processingTime='30 seconds') \
        .start()
    
    print("✅ Analytic 2: Severity Distribution - STARTED")
    
    # ============================================
    # ANALYTIC 3: Temporal Patterns (Day/Hour)
    # ============================================
    print("Setting up Analytic 3: Temporal Patterns")
    
    temporal_patterns = severity_df \
        .withColumn("day_of_week", dayofweek("event_timestamp")) \
        .withColumn("hour_of_day", hour("event_timestamp")) \
        .groupBy("day_of_week", "hour_of_day") \
        .agg(
            count("*").alias("event_count"),
            count(col("patient_id")).alias("unique_patients")
        ) \
        .withColumn("last_updated", current_timestamp())
    
    # Write Analytic 3 to PostgreSQL
    query3 = temporal_patterns \
        .writeStream \
        .outputMode("complete") \
        .foreachBatch(lambda df, epoch_id: write_to_postgres(df, "temporal_patterns", "overwrite")) \
        .trigger(processingTime='30 seconds') \
        .start()
    
    print("✅ Analytic 3: Temporal Patterns - STARTED")
    
    print("=" * 60)
    print("All 3 Analytics Running Successfully!")
    print("Writing to PostgreSQL every 30 seconds...")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Wait for all queries to finish
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()
