import os
import uvicorn
from fastapi import FastAPI

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-fastapi-images-manager'

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

from utils_module.cache_manager import CacheManager
from fastapi_module import create_collection_router
from routers.html_router import create_router as create_html_router

minio_config = config.get_value('minio')
s3_client = boto3.client('s3',
                         endpoint_url=minio_config.get('endpoint'),
                         aws_access_key_id=minio_config.get('access_key'),
                         aws_secret_access_key=minio_config.get('secret_key'),
                         config=Config(signature_version='s3v4'))
data_model_config = config.get_value('data_model')
data_model_bucket = minio_config['data_model_bucket']
cache_manager = CacheManager(s3_client, data_model_bucket)
data_model = cache_manager.get_obj(**data_model_config)

collection_router = create_collection_router(cache_manager, data_model_config['file_name'], data_model)
html_router = create_html_router(s3_client)

app = FastAPI()
app.include_router(collection_router, prefix=app_config['api_prefix'])
app.include_router(html_router, prefix=app_config['api_prefix'])

# endregion


if __name__ == '__main__':
    logger.info({'message': 'server start', 'port': app_config['port']})
    uvicorn.run('app:app', host="0.0.0.0", port=app_config['port'])
