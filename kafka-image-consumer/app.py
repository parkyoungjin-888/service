import os
import cv2
import time
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton
from kafka_module.kafka_consumer import KafkaConsumerControl
from data_model_module.raw_data_model import Imgdata
from src.grid_fs_control import GridFSControl


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'kafka-image-consumer-001'

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
CONSUMING_LATENCY = Histogram('producing_latency', 'image send latency')
CONSUMING_COUNT = Counter('producing_count', 'total number of send img')

kafka_consumer = KafkaConsumerControl(**config.get_value('kafka'))
grid_fs_control = GridFSControl(**config.get_value('grid_fs'))


def store_img(messages: dict):
    consuming_start = time.time()
    img_data = Imgdata(**messages).get_dict_with_img_decoding()
    _, img_encoded = cv2.imencode('.jpg', img_data['img'])
    img_bytes = img_encoded.tobytes()
    del img_data['img']

    grid_fs_control.upload(img_bytes, img_data)

    CONSUMING_COUNT.inc(1)
    CONSUMING_LATENCY.observe(time.time() - consuming_start)

# endregion


if __name__ == '__main__':
    kafka_consumer.start_consumer(store_img)
