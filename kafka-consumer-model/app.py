import asyncio
from config_module import init_config_and_logger

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-kafka-consumer-model'
config, logger = init_config_and_logger(local_config_host, local_config_port, local_app_id)


async def main():
    import boto3
    from botocore.client import Config
    from kafka_module.kafka_consumer import KafkaConsumerControl
    from utils_module.cache_manager import CacheManager
    from mongodb_module.beanie_client import CollectionClient

    # minio client 생성
    minio_config = config.get_value('minio')
    s3_client = boto3.client(
        's3',
        endpoint_url=minio_config.get('endpoint'),
        aws_access_key_id=minio_config.get('access_key'),
        aws_secret_access_key=minio_config.get('secret_key'),
        config=Config(signature_version='s3v4')
    )

    # cache manager 생성
    cache_bucket = minio_config['bucket']
    file_cache_dir = './tmp/cache'
    cache_manager = CacheManager(s3_client, cache_bucket, file_cache_dir)

    # data model 객체 로드
    data_model_config = config.get_value('data_model')
    data_model = cache_manager.get_obj(**data_model_config)

    # model inference 객체 로드
    model_inference_config = config.get_value('model_inference')
    weight_path = model_inference_config.pop('weight_path')
    cache_manager.download_file(weight_path)
    ModelInference = cache_manager.get_obj(**model_inference_config)

    # mongo collection client 로드
    collection_config = config.get_value('grpc-collection-manager')
    collection_model = cache_manager.get_obj(
        file_name=collection_config.pop('file_name'),
        obj_name=collection_config.pop('obj_name')
    )
    collection_client = CollectionClient(**collection_config, collection_model=collection_model)

    # inference 와 kafka consumer 생성 및 consumer 동작 시작
    inference = ModelInference(data_model, f'{file_cache_dir}/{weight_path}', s3_client, collection_client)
    kafka_consumer = KafkaConsumerControl(**config.get_value('kafka'))
    await kafka_consumer.start_consumer_async(inference.run)


if __name__ == "__main__":
    asyncio.run(main())
