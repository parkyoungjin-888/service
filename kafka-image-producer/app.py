from config_module import init_config_and_logger

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-kafka-image-producer'
config, logger = init_config_and_logger(local_config_host, local_config_port, local_app_id)


def main():
    import time
    import boto3
    from botocore.client import Config
    from utils_module.cache_manager import CacheManager
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    from redis_module.redis_stream_control import RedisStreamControl
    from kafka_module.kafka_producer import KafkaProducerControl

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
    cache_manager = CacheManager(s3_client, cache_bucket)

    # data model 객체 로드
    data_model_config = config.get_value('data_model')
    data_model = cache_manager.get_obj(**data_model_config)

    # prometheus 메트릭 선언
    start_http_server(config.get_value('prometheus_port'))
    PRODUCING_LATENCY = Histogram('producing_latency', 'image send latency')
    PRODUCING_COUNT = Counter('producing_count', 'total number of send img')

    # redis control 및 kafka producer 생성
    redis_stream_control = RedisStreamControl(**config.get_value('redis'), data_model=data_model)
    kafka_producer = KafkaProducerControl(**config.get_value('kafka'))
    batch_size = config.get_value('batch_size')

    while True:
        try:
            producing_start = time.time()
            read_data = redis_stream_control.get_data(count=batch_size)
            if read_data is None:
                continue

            for data in read_data:
                kafka_producer.send(data)
            PRODUCING_COUNT.inc(len(read_data))
            PRODUCING_LATENCY.observe(time.time() - producing_start)
            logger.debug({'message': 'producing success', 'count': len(read_data)})

        except Exception as e:
            logger.error(e)
        finally:
            time.sleep(0.1)


if __name__ == "__main__":
    main()
