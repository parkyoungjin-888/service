import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType, DoubleType
import base64
import boto3
from pymongo import MongoClient
from datetime import datetime, timezone


KAFKA_SERVERS = ("kafka-0.kafka.kafka.svc.cluster.local:9092,"
                 "kafka-1.kafka.kafka.svc.cluster.local:9092,"
                 "kafka-2.kafka.kafka.svc.cluster.local:9092")
KAFKA_TOPIC = "WEBCAM"

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY_ID")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_ACCESS_KEY")
MINIO_BUCKET = "images"

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB", "my_db")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "images")


def save_to_mongo(client, document):
    try:
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        collection.update_one({'name': document['name']}, document, upsert=True)
    except Exception as e:
        print(f"error in save_to_mongo: {e}")


def save_to_minio(image_base64, img_path):
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY
        )
        image_bytes = base64.b64decode(image_base64)
        s3.put_object(Bucket=MINIO_BUCKET, Key=img_path, Body=image_bytes)
        return "success"
    except Exception as e:
        print(f"error in save_to_minio: {e}")
        return str(e)


def process_batch(df_batch, batch_id):
    print(f'batch_id: {batch_id}')
    client = MongoClient(MONGO_URI)
    records = df_batch.collect()
    for row in records:
        try:
            timestamp = row["timestamp"]
            event_datetime = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            process_datetime = datetime.now(timezone.utc)
            img_path = f"{row['device_id']}/{row['name']}"
            save_to_mongo(client, {
                "device_id": row["device_id"],
                "name": row["name"],
                "timestamp": timestamp,
                "event_datetime": event_datetime,
                "process_datetime": process_datetime,
                "width": row["width"],
                "height": row["height"],
                "img_path": img_path
            })
            save_to_minio(row["img"], img_path)
        except Exception as e:
            print(f"Failed to save {row['name']} from {row['device_id']}: {e}")
    client.close()


spark = SparkSession.builder \
    .appName("KafkaImageToMinIO") \
    .getOrCreate()

schema = StructType() \
    .add("device_id", StringType()) \
    .add("name", StringType()) \
    .add("timestamp", DoubleType()) \
    .add("width", StringType()) \
    .add("height", StringType()) \
    .add("img", StringType())

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

query = parsed_df.writeStream \
    .foreachBatch(process_batch) \
    .outputMode("append") \
    .start()

query.awaitTermination()
