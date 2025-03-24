import os
import sys
import signal
import time
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from config_module.config_singleton import ConfigSingleton
from redis_module.redis_stream_control import RedisStreamControl
from kafka_module.kafka_producer import KafkaProducerControl


# region ############################## config section ##############################

local_config_host = '192.168.0.100'
local_config_port = 31001
local_app_id = 'queue-kafka-producer-002'

config = ConfigSingleton()
config_host = os.environ.get('CONFIG_HOST') if os.environ.get('CONFIG_HOST') else local_config_host
config_port = int(os.environ.get('CONFIG_PORT')) if os.environ.get('CONFIG_PORT') else local_config_port

app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
config.load_config(host=config_host, port=config_port, app_id=app_id)
print(f'config load data, host : "{config_host}", port : {config_port}, app_id : {app_id}')

# endregion

# region ############################## service define section ##############################

start_http_server(config.get_value('prometheus_port'))
PRODUCING_LATENCY = Histogram('producing_latency', 'image send latency')
PRODUCING_COUNT = Counter('producing_count', 'total number of send img')

redis_stream_control = RedisStreamControl(**config.get_value('redis'))
kafka_producer = KafkaProducerControl(**config.get_value('kafka'))
batch_size = config.get_value('batch_size')
data_type = config.get_value('data_type')

data_type_list = ['RAW', 'IMG']
if data_type not in data_type_list:
    raise Exception(f'data_type = {data_type} is not defined, data_type must in {data_type_list}')

func_map = {
        'RAW': {
            'read_func': redis_stream_control.get_raw_data,
            'send_func': kafka_producer.send_data
        },
        'IMG': {
            'read_func': redis_stream_control.get_img_data,
            'send_func': kafka_producer.send_img
        }
    }


def producing():
    read_func = func_map[data_type]['read_func']
    send_func = func_map[data_type]['send_func']

    while True:
        try:
            producing_start = time.time()
            read_data = read_func(count=batch_size)
            if read_data is None:
                continue

            for data in read_data['batch']:
                send_func(**data)
            PRODUCING_COUNT.inc(len(read_data['batch']))
            PRODUCING_LATENCY.observe(time.time() - producing_start)

        except Exception as e:
            print(f'Error in run: {e}')
        finally:
            time.sleep(0.1)

# endregion


# def signal_handler(sig, frame):
#     kafka_producer.close()
#     sys.exit(0)


if __name__ == "__main__":
    # signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler)

    producing()
    # image rebuild
