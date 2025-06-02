import os
from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-grpc-collection-manager'

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

import grpc
import asyncio
from concurrent import futures
import boto3
from botocore.client import Config
from utils_module.cache_manager import CacheManager
from mongodb_module.proto.collection_pb2_grpc import add_CollectionServerServicer_to_server
from mongodb_module.beanie_control import BeanieControl
from src.colletion_server import CollectionServer


minio_config = config.get_value('minio')
s3_client = boto3.client('s3',
                         endpoint_url=minio_config.get('endpoint'),
                         aws_access_key_id=minio_config.get('access_key'),
                         aws_secret_access_key=minio_config.get('secret_key'),
                         config=Config(signature_version='s3v4'))

data_model_config = config.get_value('data_model')
data_model_bucket = minio_config['data_model_bucket']
cache_manager = CacheManager(s3_client, data_model_bucket)


async def serve():
    data_model = cache_manager.get_obj(**data_model_config)

    mongo_config = config.get_value('mongo')
    beanie_control = BeanieControl(**mongo_config)
    data_model = await beanie_control.init(data_model)

    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    collection_server = CollectionServer(data_model, cache_manager, data_model_config['file_name'])
    add_CollectionServerServicer_to_server(collection_server, server)
    server.add_insecure_port(f'[::]:{app_config['port']}')

    await server.start()
    logger.info(f'{app_config['name']} serve start : 0.0.0.0:{app_config['port']}')
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=10)

# endregion


if __name__ == '__main__':
    asyncio.run(serve())
