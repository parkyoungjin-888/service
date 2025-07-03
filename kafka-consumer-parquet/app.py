from config_module import init_config_and_logger
import time
import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
import uuid
from datetime import datetime, timezone, timedelta

from prometheus_client import Counter, Histogram, start_http_server
import boto3
from botocore.client import Config

from bytewax.connectors.kafka import KafkaSource
from bytewax.connectors.stdio import StdOutSink
from bytewax.dataflow import Dataflow
from bytewax import operators as op

from utils_module.cache_manager import CacheManager


local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-kafka-consumer-parquet'
config, logger = init_config_and_logger(local_config_host, local_config_port, local_app_id)


# Prometheus 메트릭
start_http_server(config.get_value('prometheus_port'))
CONSUMING_LATENCY = Histogram('consuming_latency_seconds', 'End-to-end message processing latency')
CONSUMING_COUNT = Counter('consuming_count', 'Total number of processed messages')

parquet_config = config.get_value('parquet')
parquet_pooling = timedelta(seconds=parquet_config['pooling'])
parquet_max_count = parquet_config['max_count']

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

# MinIO (S3)
minio_config = config.get_value('minio')
s3_client = boto3.client(
    's3',
    endpoint_url=minio_config['endpoint'],
    aws_access_key_id=minio_config['access_key'],
    aws_secret_access_key=minio_config['secret_key'],
    config=Config(signature_version='s3v4')
)


def parse_message(message):
    try:
        start_time = time.time()
        json_msg = json.loads(message.value)
        event_datetime_str = json_msg.pop('event_datetime_str')
        datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        json_msg['event_datetime'] = datetime.strptime(event_datetime_str, datetime_format)
        json_msg['start_time'] = start_time
        return 'singleton', json_msg
    except Exception as e:
        logger.error(f"[parse_message] Error: {e}")
        return None


def save_to_parquet(batch):
    try:
        if not batch:
            return

        key, records = batch
        start_time = records[0].pop('start_time', time.time())

        df = pd.DataFrame(records).drop(columns='start_time', errors='ignore')
        if 'name' in df.columns:
            df.drop_duplicates(subset=['name'], keep='last', inplace=True)

        table = pa.Table.from_pandas(df)
        now = datetime.now()
        now_str = now.strftime('%Y%m%d_%H%M%S')
        category_path = parquet_config['category']
        date_path = now.strftime('%Y_%m_%d')
        file_name = f'{now_str}_{uuid.uuid4().hex[:8]}.parquet'
        object_key = f'{category_path}/{date_path}/{file_name}'

        buffer = BytesIO()
        pq.write_table(table, buffer)
        buffer.seek(0)

        res = s3_client.put_object(
            Bucket=parquet_config['bucket'],
            Key=object_key,
            Body=buffer.getvalue(),
            ContentType="application/octet-stream"
        )
        if res['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info(f'{file_name} upload success')
        else:
            logger.error(f'{file_name} upload failed')

        batch_size = len(batch)
        CONSUMING_COUNT.inc(batch_size)
        if batch_size > 0:
            CONSUMING_LATENCY.observe((time.time() - start_time)/batch_size)
    except Exception as e:
        logger.error(f"[save_to_minio] Error: {e}")


flow = Dataflow('kafka-consumer-parquet')
kafka_input = op.input('kafka-in', flow, kafka_source)
parsed = op.map('parse', kafka_input, parse_message)
batched = op.collect('collection', parsed, timeout=parquet_pooling, max_size=parquet_max_count)
saved_parquet = op.map('save-parquet', batched, save_to_parquet)
op.output('stdout', saved_parquet, StdOutSink())


if __name__ == '__main__':
    from bytewax.testing import cluster_main
    cluster_main(flow, [], proc_id=0)
