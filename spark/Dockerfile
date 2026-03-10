# Use official Spark image as base
FROM apache/spark-py:v3.3.0

# Switch to root for installations
USER root

# Install dependencies
RUN pip install --no-cache-dir \
    pyspark==3.3.0 \
    py4j==0.10.9.5

# Create app directory
WORKDIR /app

# Copy Python application
COPY spark_job.py /app/

# Download PostgreSQL JDBC driver
# RUN wget -P /opt/spark/jars/ https://jdbc.postgresql.org/download/postgresql-42.5.0.jar
RUN apt-get update && \
    apt-get install -y wget && \
    wget -P /opt/spark/jars/ https://jdbc.postgresql.org/download/postgresql-42.5.0.jar && \
    rm -rf /var/lib/apt/lists/*
# Create checkpoint directory
RUN mkdir -p /tmp/checkpoint && chmod -R 777 /tmp/checkpoint

# Switch back to spark user
USER 185

# Set environment variables
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin

# Run the application
CMD ["spark-submit", \
     "--master", "local[*]", \
     "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.postgresql:postgresql:42.5.0", \
     "--conf", "spark.sql.streaming.checkpointLocation=/tmp/checkpoint", \
     "/app/spark_job.py"]
