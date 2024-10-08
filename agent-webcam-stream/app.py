import sys
import signal
import threading
import time
from datetime import datetime
import cv2

from config_module.config_singleton import ConfigSingleton
from redis_module.redis_stream_control import RedisStreamControl


class CamStream:
    def __init__(self, redis: dict, device: int = 0, img_w: int = None, img_h: int = None, fps: int = None,
                 show_img: bool = False):
        self.device = device
        self.img_w = img_w
        self.img_h = img_h
        self.fps = fps

        self._redis = RedisStreamControl(**redis)
        self._img_data_list = []

        self.show_img = show_img
        self.running = True

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

    def capture(self):
        while self.running:
            try:
                self._connect()

                prev_time = datetime.now().timestamp()
                frame_count = 0
                fps = -1
                while self.running:
                    ret, img = self.cap.read()
                    if not ret:
                        print('cap read is failed')
                        break

                    _timestamp = datetime.now().timestamp()
                    frame_count += 1

                    img_data = {
                        'name': f'webcam.jpg',
                        'timestamp': _timestamp,
                        'width': img.shape[1],
                        'height': img.shape[0],
                        'img': img
                    }
                    self._img_data_list.append(img_data)

                    if self.show_img:
                        if _timestamp - prev_time > 1:
                            fps = frame_count
                            frame_count = 0
                            prev_time = _timestamp
                        cv2.putText(img, f'FPS: {fps}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow('img', img)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break

            except Exception as e:
                print(f'Error in stream: {e}')
            finally:
                self.close()

    def send_stream(self):
        while self.running:
            try:
                data_index = len(self._img_data_list)-1
                send_data_list = self._img_data_list[:data_index]
                data_ids = self._redis.put_img_data(**{'data': send_data_list})
                del self._img_data_list[:data_index]
                # print(f'send data_ids : {data_ids}')
                print(f'send data count : {len(data_ids)}')

                time.sleep(1)
            except Exception as e:
                print(f'Error in trim_stream: {e}')
            finally:
                pass

    def trim_stream(self):
        while self.running:
            try:
                remove_count = self._redis.remove_expired_data()
                if remove_count != 0:
                    print(f'remove_count : {remove_count}')
                time.sleep(1)
            except Exception as e:
                print(f'Error in trim_stream: {e}')
            finally:
                pass

    def close(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        print('cam release is completed')


def signal_handler(sig, frame):
    cam.close()
    time.sleep(1)
    sys.exit(0)


if __name__ == "__main__":
    config = ConfigSingleton()
    config.load_config('192.168.0.104', 31001, 'agent-webcam-stream-001')

    cam = CamStream(**config.get_value('webcam'))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    capture_thread = threading.Thread(target=cam.capture)
    send_thread = threading.Thread(target=cam.send_stream)
    trim_thread = threading.Thread(target=cam.trim_stream)

    capture_thread.start()
    send_thread.start()
    trim_thread.start()

    capture_thread.join()
    send_thread.join()
    trim_thread.join()
    # test
