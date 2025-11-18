import os
import boto3
from typing import Type
from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton
from mongodb_module.beanie_client import CollectionClient
from data_model_module.custom_base_model import CustomBaseModel


class ImagesEventHandler:
    def __init__(self, images_data_model: Type[CustomBaseModel], s3_client: boto3.client):
        config = ConfigSingleton()
        app_config = config.get_value('app')
        images_client_config = config.get_value('grpc-images-manager')
        self.images_client = CollectionClient(**images_client_config, collection_model=images_data_model)

        log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
        self.logger = LoggerSingleton.get_logger(f'{app_config['name']}.handler', level=log_level)

        self.s3_client = s3_client

    def process_insert(self, event: dict):
        pass

    def process_update(self, event: dict):
        pass

    def process_delete(self, event: dict):
        before_doc = event.get('before_doc')
        if before_doc is None:
            pass
        elif before_doc.get('img_path'):
            s3_res = self.s3_client.delete_object(Bucket='images', Key=before_doc['img_path'])
            self.logger.info({'response': s3_res})

    def process_replace(self, event: dict):
        pass

    def process(self, event: dict):
        if event.get('collection') != 'images':
            return

        self.logger.info({'message': 'receive event', 'event': event})

        operation_type = event.get('operation_type')
        if operation_type == 'insert':
            self.process_insert(event)
        elif operation_type == 'update':
            self.process_update(event)
        elif operation_type == 'delete':
            self.process_delete(event)
        elif operation_type == 'replace':
            self.process_replace(event)
        else:
            pass
