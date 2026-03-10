from pyspark.sql import SparkSession
from pyspark.sql.functions import(col,from_json,count,avg,current_timestamp,to_timestamp,hour,dayofweek,when)

from pyspark.sql.types import StructType,StructField,StringType,IntegerType,DoubleType
from features.category_d.dq_job import run_dq_for_df, write_metric_to_db

import os

KAFKA_BOOTSTRAP_SERVERS=os.getenv("KAFKA_BOOTSTRAP_SERVERS","kafka-team07:9092")
KAFKA_TOPIC=os.getenv("KAFKA_TOPIC","ds551-f25.team07.environmental_conditions")
POSTGRES_HOST=os.getenv("POSTGRES_HOST","postgres")
POSTGRES_PORT=os.getenv("POSTGRES_PORT","5432")
POSTGRES_DB=os.getenv("POSTGRES_DB","epidemic")
POSTGRES_USER=os.getenv("POSTGRES_USER","ds551")
POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD","ds551pw")
TEAM_ID="07"

environment_schema = StructType([
    StructField("event_type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("region", StringType(), True),
    StructField("station_id", StringType(), True),
    StructField("temperature_f", DoubleType(), True),
    StructField("humidity_percent", IntegerType(), True),
    StructField("air_quality_index", IntegerType(), True),
    StructField("pollen_count", IntegerType(), True),
    StructField("uv_index", IntegerType(), True),
    StructField("wind_speed_mph", DoubleType(), True),
    StructField("processing_timestamp", StringType(), True),
    StructField("event_source", StringType(), True),
    StructField("team_id", StringType(), True)
])

def create_postgres_connection_properties():
    return {"user":POSTGRES_USER, "password":POSTGRES_PASSWORD,"driver":"org.postgresql.Driver"}

def write_to_postgres(df,table_name,mode="append"):
    jdbc_url=f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    properties=create_postgres_connection_properties()
    df.write.jdbc(url=jdbc_url,table=table_name,mode=mode,properties=properties)

def main():
    spark=SparkSession.builder.appName("EnvironmentalAnalytics-Team07")\
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,"
                "org.postgresql:postgresql:42.5.0")\
        .config("spark.sql.streaming.checkpointLocation","/tmp/checkpoint")\
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    print("-"*60)
    print("Starting second job for Environmental Analytics Team 07")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    print(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    print("-"*60)
    
    #this reads the event type data from kafka
    kafka_df=spark.readStream.format("kafka").option("kafka.bootstrap.servers",KAFKA_BOOTSTRAP_SERVERS).option("subscribe",KAFKA_TOPIC).option("startingOffsets","earliest").load()
    
    #parse JSON and extract the fields
    parsed_df=kafka_df.select(from_json(col("value").cast("string"),environment_schema).alias("data")).select("data.*")
    
    #Convert timestamp to proper format
    
    parsed_df=parsed_df.withColumn("event_timestamp",to_timestamp(col("timestamp"),"yyyy-MM-dd'T'HH:mm:ss.SSSSSS"))
    #------
    #First Analytic (Average temperature by Region)
    #------
    avg_temp_region=parsed_df.groupBy("region").agg((avg("temperature_f").alias("avg_temperature_f")))\
        .withColumn("last_updated",current_timestamp())
    
    query1=avg_temp_region.writeStream.outputMode("complete")\
        .foreachBatch(lambda df, _: write_to_postgres(df, "env_avg_temp", "overwrite")) \
        .start()
        
    print("Analytic 1: Average Temperature by Region Started")
    
    #----
    #Second Analytic (Air Quality Summary by Region)
    #----
    air_region=parsed_df.groupBy("region").agg(
        avg("air_quality_index").alias("avg_air_quality"),
        avg("pollen_count").alias("avg_pollen_count"),
        avg("uv_index").alias("avg_uv_index")
    ).withColumn("last_updated",current_timestamp())
    
    query2=air_region.writeStream.outputMode("complete") \
        .foreachBatch(lambda df, _: write_to_postgres(df, "env_aqi_distribution", "overwrite")) \
        .start()

    print("Analytic 2: Air Quality Summary by Region Started")
    
    #----
    #Third Analytic (Hourly Weather Trend)
    #----
    
    hourly_trends=parsed_df.withColumn("hour_of_day",hour("event_timestamp"))\
        .groupBy("hour_of_day").agg(
            avg("temperature_f").alias("average_temp"),
            avg("humidity_percent").alias("average_humidity"),
            avg("wind_speed_mph").alias("average_windspeed")
        ).withColumn("last_updated",current_timestamp())
    
    
    query3=hourly_trends.writeStream.outputMode("complete") \
        .foreachBatch(lambda df, _: write_to_postgres(df, "env_hourly_temp", "overwrite")) \
        .start()
    
    print("Analytic 3: Hourly Patterns Started")
    print("-" * 60)
    print("All 3 Analytics Running Successfully!")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    spark.streams.awaitAnyTermination()
    
if __name__=="__main__":
    main()