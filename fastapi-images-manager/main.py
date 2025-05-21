import os
import uvicorn
from fastapi import FastAPI

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-fastapi-image-streaming'

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

from data_model_module.model_cashe_manager import ModelCacheManager
from fastapi_module import create_collection_router

minio_config = config.get_value('minio')
s3_client = boto3.client('s3',
                         endpoint_url=minio_config.get('endpoint'),
                         aws_access_key_id=minio_config.get('access_key'),
                         aws_secret_access_key=minio_config.get('secret_key'),
                         config=Config(signature_version='s3v4'))

data_model_config = config.get_value('data_model')
data_model_name = data_model_config['model_name']
model_manager = ModelCacheManager(s3_client, minio_config['bucket'], data_model_config['file_name'])
data_model = model_manager.get_model(data_model_name)
collection_router = create_collection_router(model_manager, data_model)

app = FastAPI()
app.include_router(collection_router, prefix=app_config['api_prefix'])

# endregion


if __name__ == '__main__':
    logger.info({'message': 'server start', 'port': app_config['port']})
    uvicorn.run('main:app', host="0.0.0.0", port=app_config['port'])
