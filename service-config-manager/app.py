import os
import grpc
from concurrent import futures
from config_module.proto import config_pb2
from config_module.proto import config_pb2_grpc
from config_module.config_loader import ConfigLoader


# region ############################## config section ##############################

local_config_url = 'mongodb://your-username:your-password@192.168.0.105:27017,192.168.0.105:27018/?replicaSet=rs0'
local_app_id = 'service-config-manager-001'

config_url = os.environ.get('CONFIG_URL') if os.environ.get('CONFIG_URL') else local_config_url
app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
config_loader = ConfigLoader(config_db_path=config_url, app_id=app_id)
print(f'config load data, url : "{config_url}", app_id : {app_id}')

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
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    config_pb2_grpc.add_ConfigServerServicer_to_server(ConfigServer(), server)
    server.add_insecure_port(f'[::]:{config_loader.port}')
    server.start()

    print(f'{config_loader.name} serve start : 0.0.0.0:{config_loader.port}')

    server.wait_for_termination()

# endregion


if __name__ == '__main__':
    serve()
