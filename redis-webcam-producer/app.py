import os

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton
from src.cam_stream import CamStream


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-redis-webcam-producer'

config_host = os.environ.get('CONFIG_HOST', local_config_host)
config_port = int(os.environ.get('CONFIG_PORT', local_config_port))
app_id = os.environ.get('APP_ID', local_app_id)

config = ConfigSingleton()
config.load_config(host=config_host, port=config_port, app_id=app_id)

app_config = config.get_value('app')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.main', level=log_level)
logger.info({'message': 'config load success', 'host': config_host, 'port': config_port, 'app_id': app_id})

# endregion

# region ############################## service define section ##############################

cam = CamStream()

# endregion


if __name__ == "__main__":
    cam.steam()
