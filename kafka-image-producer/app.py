import os
import time
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton
from redis_module.redis_stream_control import RedisStreamControl
from kafka_module.kafka_producer import KafkaProducerControl


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-kafka-image-producer'

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

start_http_server(config.get_value('prometheus_port'))
PRODUCING_LATENCY = Histogram('producing_latency', 'image send latency')
PRODUCING_COUNT = Counter('producing_count', 'total number of send img')

redis_stream_control = RedisStreamControl(**config.get_value('redis'))
kafka_producer = KafkaProducerControl(**config.get_value('kafka'))
batch_size = config.get_value('batch_size')


def producing():
    read_func = redis_stream_control.get_img_data
    send_func = kafka_producer.send_img

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
            logger.debug({'message': 'producing success', 'count': len(read_data['batch'])})

        except Exception as e:
            logger.error(e)
        finally:
            time.sleep(0.1)

# endregion


if __name__ == "__main__":
    producing()
