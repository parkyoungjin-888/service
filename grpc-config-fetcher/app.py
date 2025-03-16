import os
import grpc
from concurrent import futures
from config_module.proto import config_pb2
from config_module.proto import config_pb2_grpc
from config_module.config_loader import ConfigLoader
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

port = os.environ.get('CONFIG_URL', 21001)

local_config_url = f'mongodb://yj:dudwls123@192.168.0.104:27017'
config_url = os.environ.get('CONFIG_URL', local_config_url)
config_loader = ConfigLoader(config_db_path=config_url)

logger = LoggerSingleton.get_logger('app_logger', file_name='./log/app.log', level='DEBUG')
logger.info(f'config load data, config_url : {config_url}')

# endregion

# region ############################## service define section ##############################


class ConfigServer(config_pb2_grpc.ConfigServerServicer):
    def GetConfig(self, request, context):
        app_id = request.app_id
        config = config_loader.get_config(app_id)
        unpack_config = config_loader.unpack_config(config)

        res_payload = map(lambda x: config_pb2.KeyValue(key=x['key'], value=x['value'], type=x['type']), unpack_config)
        response = config_pb2.ConfigReply()
        response.config_data.extend(list(res_payload))
        logger.info({'app_id': app_id, 'res': config})
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    config_pb2_grpc.add_ConfigServerServicer_to_server(ConfigServer(), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()

    logger.info(f'config serve start : 0.0.0.0:{port}')

    server.wait_for_termination()

# endregion


if __name__ == '__main__':
    serve()
