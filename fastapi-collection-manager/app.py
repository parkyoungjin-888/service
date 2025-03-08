import os
import logging
import uvicorn
from fastapi import FastAPI

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'fastapi-collection-server-001'

config = ConfigSingleton()
config_host = os.environ.get('CONFIG_HOST') if os.environ.get('CONFIG_HOST') else local_config_host
config_port = int(os.environ.get('CONFIG_PORT')) if os.environ.get('CONFIG_PORT') else local_config_port

logger = LoggerSingleton.get_logger('app_logger', file_name='./log/app.log', level=logging.DEBUG)

app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
config.load_config(host=config_host, port=config_port, app_id=app_id)
logger.info(f'config load data, host : {config_host}, port : {config_port}, app_id : {app_id}')

# endregion

# region ############################## service define section ##############################

from src.routes.collection_routes import router as collection_router

app_config = config.get_value('app')

app = FastAPI()
app.include_router(collection_router, prefix=app_config['api_prefix'])

# endregion


if __name__ == '__main__':
    uvicorn.run('app:app', host="0.0.0.0", port=app_config['port'], reload=True)
