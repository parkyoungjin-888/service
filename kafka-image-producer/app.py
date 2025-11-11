from config_module import init_config_and_logger

local_config_host = '192.168.35.104'
local_config_port = 21001
local_app_id = 'local-kafka-image-producer'
config, logger = init_config_and_logger(local_config_host, local_config_port, local_app_id)


def main():
    import time
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    from redis_module.redis_stream_control import RedisStreamControl
    from kafka_module.kafka_producer import KafkaProducerControl

    # prometheus 메트릭 선언
    start_http_server(config.get_value('prometheus_port'))
    PRODUCING_LATENCY = Histogram('producing_latency', 'image send latency')
    PRODUCING_COUNT = Counter('producing_count', 'total number of send img')

    # redis control 및 kafka producer 생성
    redis_stream_control = RedisStreamControl(**config.get_value('redis'))
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
