import os
import sys
import signal
import threading
import asyncio
import time
from datetime import datetime
import cv2

from config_module.config_singleton import ConfigSingleton
from redis_module.redis_stream_control import RedisStreamControl


class CamStream:
    def __init__(self,
                 redis_control: RedisStreamControl,
                 device: int = 0, img_w: int = None, img_h: int = None, fps: int = None,
                 show_img: bool = False):
        self.device = device
        self.img_w = img_w
        self.img_h = img_h
        self.fps = fps
        self._redis = redis_control
        self.show_img = show_img
        self.in_streaming = False

        self._loop = asyncio.get_event_loop()
        self._img_queue = asyncio.Queue()

    def _connect(self):
        self.cap = cv2.VideoCapture(self.device)
        if self.img_w is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.img_w)
        if self.img_h is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.img_h)
        if self.fps is not None:
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        if not self.cap.isOpened():
            raise Exception(f'Cannot open cam {self.device}')

    async def _capture(self):
        while True:
            try:
                self._connect()

                prev_time = datetime.now().timestamp()
                frame_count = 0
                fps = -1
                img_data_list = []
                while True:
                    ret, img = self.cap.read()
                    if not ret:
                        print('cap read is failed')
                        self.in_streaming = False
                        break
                    else:
                        self.in_streaming = True

                    _timestamp = datetime.now().timestamp()
                    frame_count += 1

                    img_data = {
                        'name': f'webcam.jpg',
                        'timestamp': _timestamp,
                        'width': img.shape[1],
                        'height': img.shape[0],
                        'img': img
                    }
                    img_data_list.append(img_data)

                    if _timestamp - prev_time > 1:
                        fps = frame_count
                        frame_count = 0
                        prev_time = _timestamp
                        await self._img_queue.put(img_data_list)
                        img_data_list = []

                    if self.show_img:
                        cv2.putText(img, f'FPS: {fps}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow('img', img)
                        if cv2.waitKey(1) & 0xFF == 27 or cv2.waitKey(1) & 0xFF == ord('q'):
                            break

                    await asyncio.sleep(0.01)

            except Exception as e:
                print(f'Error in stream: {e}')
            finally:
                self.close()

    async def _send_stream(self):
        while True:
            try:
                if self._img_queue.qsize() <= 0:
                    continue

                send_data_list = await self._img_queue.get()

                # data_index = len(self._img_queue)-1
                # send_data_list = self._img_queue[:data_index]

                data_ids = self._redis.put_img_data(**{'batch': send_data_list})
                # del self._img_queue[:data_index]
                print(f'send data count : {len(data_ids)}')

            except Exception as e:
                print(f'Error in send_stream: {e}')
            finally:
                await asyncio.sleep(1)

    async def _trim_stream(self):
        while True:
            try:
                remove_count = self._redis.remove_expired_data()
                if remove_count != 0:
                    print(f'remove_count : {remove_count}')

                # time.sleep(0.2)
            except Exception as e:
                print(f'Error in trim_stream: {e}')
            finally:
                await asyncio.sleep(1)

    def steam(self):
        self._loop.create_task(self._capture())
        self._loop.create_task(self._send_stream())
        self._loop.create_task(self._trim_stream())
        self._loop.run_forever()

    def close(self):
        self.in_streaming = False
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        print('cam release is completed')


def signal_handler(sig, frame):
    cam.close()
    sys.exit(0)


if __name__ == "__main__":
    local_config_host = '192.168.0.104'
    local_config_port = 31001
    local_app_id = 'agent-webcam-stream-001'

    config = ConfigSingleton()
    config_host = os.environ.get('CONFIG_HOST') if os.environ.get('CONFIG_HOST') else local_config_host
    config_port = int(os.environ.get('CONFIG_PORT')) if os.environ.get('CONFIG_PORT') else local_config_port

    app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
    config.load_config(host=config_host, port=config_port, app_id=app_id)
    print(f'config load data, host : {config_host}, port : {config_port}, app_id : {app_id}')

    redis_config = config.get_value('redis')
    redis_stream_control = RedisStreamControl(**redis_config)

    cam_config = config.get_value('webcam')
    cam = CamStream(**cam_config, redis_control=redis_stream_control)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    cam.steam()
