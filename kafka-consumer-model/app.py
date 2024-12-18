import os
import time

import cv2
import numpy as np
import onnxruntime as ort

from config_module.config_singleton import ConfigSingleton
from kafka_module.kafka_consumer import KafkaConsumerControl
from data_model_module.raw_data_model import Imgdata


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 31001
local_app_id = 'kafka-consumer-model-001'

config = ConfigSingleton()
config_host = os.environ.get('CONFIG_HOST') if os.environ.get('CONFIG_HOST') else local_config_host
config_port = int(os.environ.get('CONFIG_PORT')) if os.environ.get('CONFIG_PORT') else local_config_port

app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
config.load_config(host=config_host, port=config_port, app_id=app_id)
print(f'config load data, host : "{config_host}", port : {config_port}, app_id : {app_id}')

# endregion

# region ############################## service define section ##############################

kafka_consumer = KafkaConsumerControl(**config.get_value('kafka'))


def box_cxcywh_to_xyxy(box_array):
    box_array = np.asarray(box_array)
    x_c, y_c, w, h = box_array[:, 0], box_array[:, 1], box_array[:, 2], box_array[:, 3]
    b = np.stack([
        x_c - 0.5 * w,  # x_min
        y_c - 0.5 * h,  # y_min
        x_c + 0.5 * w,  # x_max
        y_c + 0.5 * h  # y_max
    ], axis=1)
    return b


def rescale_bboxes(out_bbox, size):
    img_w, img_h = size
    b = box_cxcywh_to_xyxy(out_bbox)
    b = b * np.array([img_w, img_h, img_w, img_h], dtype=np.float32)
    return b


class ModelInference:
    def __init__(self):
        self.input_size = (640, 480)
        onnx_model_path = './optimized_val_beat-epoch=181-val_loss=0.58.onnx'
        self.session = ort.InferenceSession(onnx_model_path)
        self.input_name = self.session.get_inputs()[0].name

        self.mean = [0.485, 0.456, 0.406]
        self.std = [0.229, 0.224, 0.225]

    def preprocess_img(self, img):
        crop_img = img[120:600, 320:960]
        img_array = np.array(crop_img, dtype=np.float32)
        img_array = (img_array / 255.0 - self.mean) / self.std
        img_array = np.transpose(img_array, (2, 0, 1))
        img_array = np.expand_dims(img_array, axis=0)
        return img_array.astype(np.float32)

    def run(self, messages: dict):
        start = time.time()
        img_data = Imgdata(**messages).get_dict_with_img_decoding()
        img_array = self.preprocess_img(img_data['img'])

        outputs = self.session.run(None, {self.input_name: img_array})

        predicted_labels = np.squeeze(outputs[0])

        exps = np.exp(predicted_labels)
        softmax_result = (exps / np.sum(exps, axis=-1, keepdims=True))[:, :-1]

        threshold = 0.7
        max_values = np.max(softmax_result, axis=-1)
        indices = np.where(max_values >= threshold)
        max_label = [np.argmax(predicted_labels[idx], axis=-1) for idx in zip(*indices)]

        predicted_boxes = np.squeeze(outputs[1])
        max_boxes = [predicted_boxes[idx] for idx in zip(*indices)]

        if len(max_boxes) > 0:
            rescale_max_boxes = rescale_bboxes(max_boxes, self.input_size)
            for label, box in zip(max_label, rescale_max_boxes):
                x_1, y_1, x_2, y_2 = (box + [320, 120, 320, 120]).astype(np.int32)
                cv2.rectangle(img_data['img'], (320, 120), (960, 600), (0, 0, 255), 1)
                cv2.rectangle(img_data['img'], (x_1, y_1), (x_2, y_2), (0, 255, 0), 1)
                cv2.putText(img_data['img'], str(label), (x_1, y_1), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1)
            tact = str(time.time() - start)
            print(tact)
            cv2.putText(img_data['img'], tact, (50, 50), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1)
            cv2.imshow('img', img_data['img'])
            cv2.waitKey(1)


# endregion


if __name__ == "__main__":
    inference = ModelInference()
    kafka_consumer.start_consumer(inference.run)
