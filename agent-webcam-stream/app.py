import os
# import sys
# import signal

from config_module.config_singleton import ConfigSingleton
from src.cam_stream import CamStream


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 31001
local_app_id = 'agent-webcam-stream-001'

config = ConfigSingleton()
config_host = os.environ.get('CONFIG_HOST') if os.environ.get('CONFIG_HOST') else local_config_host
config_port = int(os.environ.get('CONFIG_PORT')) if os.environ.get('CONFIG_PORT') else local_config_port

app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
config.load_config(host=config_host, port=config_port, app_id=app_id)
print(f'config load data, host : {config_host}, port : {config_port}, app_id : {app_id}')

# endregion

# region ############################## service define section ##############################

cam = CamStream()

# endregion


# def signal_handler(sig, frame):
#     cam.close()
#     sys.exit(0)


if __name__ == "__main__":
    # signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler)

    cam.steam()
