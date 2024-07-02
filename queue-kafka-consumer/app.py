import pandas as pd
from datetime import datetime

from config_module.config_singleton import ConfigSingleton
from kafka_module.kafka_consumer import KafkaConsumerControl
from influxdb_module.influxdb_control import InfluxDbControl


config = ConfigSingleton()
config.load_config('localhost', 50050, 'queue-kafka-consumer-001')

influxdb_control = InfluxDbControl(**config.get_value('influxdb_module'))
kafka_consumer = KafkaConsumerControl(**config.get_value('kafka'))
bucket = config.get_value('influxdb.bucket')


def write_batch_data(messages: list[dict]):
    df = pd.DataFrame(messages)
    io_id_list = list(set(df['io_id']))
    for io_id in io_id_list:
        select_df = df[df['io_id'] == io_id]
        data_list = list(select_df['value'])
        datetime_list = [datetime.fromtimestamp(ts) for ts in select_df['timestamp']]
        influxdb_control.insert_data(bucket, 'test', data_list, datetime_list, [io_id])


if __name__ == "__main__":
    kafka_consumer.start_consumer(write_batch_data)
    print('testtest')
