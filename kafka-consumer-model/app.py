import os

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-kafka-consumer-model'

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

import boto3
from botocore.client import Config

from kafka_module.kafka_consumer import KafkaConsumerControl
from utils_module.cache_manager import CacheManager
from mongodb_module.beanie_client import CollectionClient

minio_config = config.get_value('minio')
s3_client = boto3.client('s3',
                         endpoint_url=minio_config.get('endpoint'),
                         aws_access_key_id=minio_config.get('access_key'),
                         aws_secret_access_key=minio_config.get('secret_key'),
                         config=Config(signature_version='s3v4'))

cache_bucket = minio_config['bucket']
file_cache_dir = './tmp/cache'
cache_manager = CacheManager(s3_client, cache_bucket, file_cache_dir)

data_model_config = config.get_value('data_model')
data_model = cache_manager.get_obj(**data_model_config)

model_inference_config = config.get_value('model_inference')
weight_path = model_inference_config.pop('weight_path')
cache_manager.download_file(weight_path)
ModelInference = cache_manager.get_obj(**model_inference_config)

kafka_consumer = KafkaConsumerControl(**config.get_value('kafka'))
collection_client = CollectionClient(**config.get_value('grpc-collection-manager'), collection_model=data_model)
inference = ModelInference(data_model, f'{file_cache_dir}/{weight_path}', s3_client)

# endregion


if __name__ == "__main__":
    kafka_consumer.start_consumer(inference.run)
