import os
import grpc
import asyncio
import logging
from concurrent import futures

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton
from mongodb_module.proto import collection_pb2_grpc
from mongodb_module.beanie_control import BeanieControl
from src.colletion_server import CollectionServer
from data_model_module.beanie_data_model.model_importer import import_model


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'grpc-img-process-manager-001'

config = ConfigSingleton()
config_host = os.environ.get('CONFIG_HOST') if os.environ.get('CONFIG_HOST') else local_config_host
config_port = int(os.environ.get('CONFIG_PORT')) if os.environ.get('CONFIG_PORT') else local_config_port

logger = LoggerSingleton.get_logger('app_logger', file_name='./log/app.log', level=logging.DEBUG)

app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
config.load_config(host=config_host, port=config_port, app_id=app_id)
logger.info(f'config load data, host : {config_host}, port : {config_port}, app_id : {app_id}')

# endregion


# region ############################## service define section ##############################

async def serve():
    data_model_name = config.get_value('data_model_name')
    data_model = import_model(data_model_name)

    mongo_config = config.get_value('mongo')
    beanie_control = BeanieControl(**mongo_config)
    data_model = await beanie_control.init(data_model)

    app_config = config.get_value('app')

    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    collection_pb2_grpc.add_CollectionServerServicer_to_server(CollectionServer(data_model), server)
    server.add_insecure_port(f'[::]:{app_config['port']}')

    await server.start()
    logger.info(f'{app_config['name']} serve start : 0.0.0.0:{app_config['port']}')
    await server.wait_for_termination()

# endregion


if __name__ == '__main__':
    asyncio.run(serve())
