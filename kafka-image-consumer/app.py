from config_module import init_config_and_logger
import time
import json
import base64
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram, start_http_server
import boto3
from botocore.client import Config
from pymongo import MongoClient

from bytewax.connectors.kafka import KafkaSource
from bytewax.connectors.stdio import StdOutSink
from bytewax.dataflow import Dataflow
from bytewax import operators as op

from utils_module.cache_manager import CacheManager


local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-kafka-image-consumer'
config, logger = init_config_and_logger(local_config_host, local_config_port, local_app_id)


# Prometheus 메트릭
start_http_server(config.get_value('prometheus_port'))
CONSUMING_LATENCY = Histogram('consuming_latency_seconds', 'End-to-end message processing latency')
CONSUMING_COUNT = Counter('consuming_count', 'Total number of processed messages')


# Kafka
kafka_config = config.get_value('kafka')
kafka_source = KafkaSource(
    brokers=kafka_config['server_urls'],
    topics=[kafka_config['topic']],
    # add_config={
    #     'group.id': kafka_config.get('group_id', 'default_group_id'),
    #     'auto.offset.reset': 'earliest',
    # } ## 동작 하지 않음
)

# MongoDB
mongo_config = config.get_value('mongo')
mongo_url = f'mongodb://{mongo_config["user"]}:{mongo_config["pwd"]}@{mongo_config["host"]}:{mongo_config["port"]}'
mongo_client = MongoClient(mongo_url)
mongo_collection = mongo_client[mongo_config['db']][mongo_config['collection']]

# MinIO (S3)
minio_config = config.get_value('minio')
s3_client = boto3.client(
    's3',
    endpoint_url=minio_config['endpoint'],
    aws_access_key_id=minio_config['access_key'],
    aws_secret_access_key=minio_config['secret_key'],
    config=Config(signature_version='s3v4')
)

# Data Model 로드
cache_manager = CacheManager(s3_client, 'cachefile')
data_model_config = config.get_value('data_model')
data_model = cache_manager.get_obj(**data_model_config)


def parse_message(message):
    try:
        start_time = time.time()
        json_msg = json.loads(message.value)
        timestamp = float(json_msg['timestamp'])

        doc = {
            'device_id': json_msg['device_id'],
            'name': json_msg['name'],
            'timestamp': timestamp,
            'event_datetime': datetime.fromtimestamp(timestamp, tz=timezone.utc),
            'process_datetime': datetime.now(timezone.utc),
            'width': json_msg['width'],
            'height': json_msg['height'],
            'img_path': f"{json_msg['device_id']}/{json_msg['name']}"
        }
        doc = data_model(**doc).model_dump()
        doc.update({'img_bytes': json_msg['img'], 'start_time': start_time})
        return doc
    except Exception as e:
        logger.error(f"[parse_message] Error: {e}")
        return None


def save_to_mongo(doc):
    try:
        img_bytes = doc.pop('img_bytes')
        start_time = doc.pop('start_time')
        mongo_collection.update_one({'name': doc['name']}, {'$set': doc}, upsert=True)
        return {'img_bytes': img_bytes, 'img_path': doc['img_path'], 'start_time': start_time}
    except Exception as e:
        logger.error(f"[save_to_mongo] Error: {e}")
        return None


def save_to_minio(img_data):
    try:
        image_bytes = base64.b64decode(img_data['img_bytes'])
        s3_client.put_object(
            Bucket=minio_config['bucket'],
            Key=img_data['img_path'],
            Body=image_bytes
        )
        CONSUMING_COUNT.inc()
        CONSUMING_LATENCY.observe(time.time() - img_data['start_time'])
    except Exception as e:
        logger.error(f"[save_to_minio] Error: {e}")


flow = Dataflow('kafka-image-consumer')

kafka_input = op.input('kafka-in', flow, kafka_source)

parsed = op.map('parse', kafka_input, parse_message)
parsed_filtered = op.filter('filter-parse', parsed, lambda x: x is not None)

saved_mongo = op.map('save-mongo', parsed_filtered, save_to_mongo)
saved_filtered = op.filter('filter-save', saved_mongo, lambda x: x is not None)

saved_minio = op.map('save-minio', saved_filtered, save_to_minio)
op.output('stdout', saved_minio, StdOutSink())


if __name__ == '__main__':
    from bytewax.testing import cluster_main
    cluster_main(flow, [], proc_id=0)
