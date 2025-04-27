import os
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'spark-image-consumer-local'

config_host = os.environ.get('CONFIG_HOST', local_config_host)
config_port = int(os.environ.get('CONFIG_PORT', local_config_port))
app_id = os.environ.get('APP_ID', local_app_id)

config = ConfigSingleton()
config.load_config(host=config_host, port=config_port, app_id=app_id)

app_config = config.get_value('app')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.main', level=log_level)

# endregion

# region ############################## service define section ##############################

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType, DoubleType
import base64
import boto3
from pymongo import MongoClient
from datetime import datetime, timezone

start_http_server(config.get_value('prometheus_port'))
CONSUMING_LATENCY = Histogram('producing_latency', 'image send latency')
CONSUMING_COUNT = Counter('producing_count', 'total number of send img')

kafka_config = config.get_value('kafka')
KAFKA_SERVERS = ','.join(kafka_config.get('server_urls', []))
KAFKA_TOPIC = kafka_config['topic']

mongo_config = config.get_value('mongo')
MONGO_URI = f'mongodb://{mongo_config["user"]}:{mongo_config["pwd"]}@{mongo_config["host"]}:{mongo_config["port"]}'
MONGO_DB = mongo_config['db']
MONGO_COLLECTION = mongo_config['collection']

minio_config = config.get_value('minio')
MINIO_ENDPOINT = minio_config['endpoint']
MINIO_ACCESS_KEY = minio_config['access_key']
MINIO_SECRET_KEY = minio_config['secret_key']
MINIO_BUCKET = minio_config['bucket']


def save_to_mongo(client, document):
    try:
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        collection.insert_one(document)
    except Exception as e:
        logger.error(f'error in save_to_mongo: {e}')


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
        return 'success'
    except Exception as e:
        logger.error(f'error in save_to_minio: {e}')
        return str(e)


def process_batch(df_batch, batch_id):
    logger.debug(f'batch_id: {batch_id}')
    client = MongoClient(MONGO_URI)
    records = df_batch.collect()
    for row in records:
        try:
            timestamp = row['timestamp']
            event_datetime = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            process_datetime = datetime.now(timezone.utc)
            img_path = f'{row["device_id"]}/{row["name"]}'
            save_to_mongo(client, {
                'device_id': row['device_id'],
                'name': row['name'],
                'timestamp': timestamp,
                'event_datetime': event_datetime,
                'process_datetime': process_datetime,
                'width': row['width'],
                'height': row['height'],
                'img_path': img_path
            })
            save_to_minio(row['img'], img_path)
        except Exception as e:
            logger.error(f'Failed to save {row["name"]} from {row["device_id"]}: {e}')
    client.close()

# endregion


if __name__ == '__main__':
    spark = SparkSession.builder \
        .appName('KafkaImageUpload') \
        .getOrCreate()

    schema = StructType() \
        .add('device_id', StringType()) \
        .add('name', StringType()) \
        .add('timestamp', DoubleType()) \
        .add('width', StringType()) \
        .add('height', StringType()) \
        .add('img', StringType())

    df = spark.readStream \
        .format('kafka') \
        .option('kafka.bootstrap.servers', KAFKA_SERVERS) \
        .option('subscribe', KAFKA_TOPIC) \
        .option('startingOffsets', 'latest') \
        .load()

    parsed_df = df.selectExpr('CAST(value AS STRING)') \
        .select(from_json(col('value'), schema).alias('data')) \
        .select('data.*')

    query = parsed_df.writeStream \
        .foreachBatch(process_batch) \
        .outputMode('append') \
        .start()

    query.awaitTermination()
