import grpc
from concurrent import futures
from config_module.proto import config_pb2
from config_module.proto import config_pb2_grpc
from config_module.config_loader import ConfigLoader

_config_url = 'mongodb://yj:dudwls123@192.168.0.104:27017,192.168.0.104:27018/?replicaSet=rs0'
_config_loader = ConfigLoader(config_db_path=_config_url,
                              app_id='service-config-manager-001')


class ConfigServer(config_pb2_grpc.ConfigServerServicer):
    def GetConfig(self, request, context):
        app_id = request.app_id
        config = _config_loader.get_config(app_id)
        unpack_config = _config_loader.unpack_config(config)

        res_payload = map(lambda x: config_pb2.KeyValue(key=x['key'], value=x['value'], type=x['type']), unpack_config)
        response = config_pb2.ConfigReply()
        response.config_data.extend(list(res_payload))
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    config_pb2_grpc.add_ConfigServerServicer_to_server(ConfigServer(), server)
    server.add_insecure_port(f'[::]:{_config_loader.port}')
    server.start()

    print(f'{_config_loader.name} serve start : 0.0.0.0:{_config_loader.port}')

    server.wait_for_termination()


if __name__ == '__main__':
    serve()
    print('1')
