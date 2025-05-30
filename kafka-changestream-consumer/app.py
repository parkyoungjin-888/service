import os

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-kafka-changestream-consumer'

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


minio_config = config.get_value('minio')
s3_client = boto3.client('s3',
                         endpoint_url=minio_config.get('endpoint'),
                         aws_access_key_id=minio_config.get('access_key'),
                         aws_secret_access_key=minio_config.get('secret_key'),
                         config=Config(signature_version='s3v4'))

kafka_config = config.get_value('kafka')
kafka_consumer = KafkaConsumerControl(**kafka_config)

cache_manager = CacheManager(s3_client, minio_config['bucket'])

handler_config = config.get_value('handler')
EventHandlerClass = cache_manager.get_obj(**handler_config)
event_handle = EventHandlerClass(config, logger, cache_manager, s3_client)

# endregion


if __name__ == '__main__':
    kafka_consumer.start_consumer(event_handle.process)
