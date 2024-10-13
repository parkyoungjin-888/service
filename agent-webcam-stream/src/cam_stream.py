import asyncio
from datetime import datetime
import cv2

from config_module.config_singleton import ConfigSingleton
from redis_module.redis_stream_control import RedisStreamControl


class CamStream:
    def __init__(self):
        config = ConfigSingleton()
        webcam_config = config.get_value('webcam')
        redis_config = config.get_value('redis')

        self.device = webcam_config['device']
        self.img_w = webcam_config['img_w']
        self.img_h = webcam_config['img_h']
        self.fps = webcam_config['fps']
        self.show_img = webcam_config['show_img']

        self._redis = RedisStreamControl(**redis_config)

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
                if not self.in_streaming or self._img_queue.qsize() <= 0:
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