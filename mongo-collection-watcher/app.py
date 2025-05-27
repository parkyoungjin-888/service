import os

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


# region ############################## config section ##############################

local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-mongo-collection-watcher'

config_host = os.environ.get('CONFIG_HOST', local_config_host)
config_port = int(os.environ.get('CONFIG_PORT', local_config_port))
app_id = os.environ.get('APP_ID', local_app_id)

config = ConfigSingleton()
config.load_config(host=config_host, port=config_port, app_id=app_id)

app_config = config.get_value('app')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.main', level=log_level)

# endregion


# region ############################## service define section ##############################

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from kafka_module.kafka_producer import KafkaProducerControl

mongo_config = config.get_value('mongo')
watch_collections = config.get_value('watch_collections')

kafka_config = config.get_value('kafka')
kafka_producer = KafkaProducerControl(**kafka_config)


def convert_for_json(data):
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            result[key] = convert_for_json(value)
        return result
    elif isinstance(data, list):
        return [convert_for_json(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.strftime('%Y-%m-%d %H:%M:%S.%f')
    else:
        return data


def make_payload(change):
    update_description = change.get('updateDescription', {})
    before_doc = change.get('fullDocumentBeforeChange')
    full_doc = change.get('fullDocument')
    payload = {
        'collection': change['ns']['coll'],
        'doc_id': change['documentKey']['_id'],
        'operation_type': change.get('operationType'),
        'update_content': update_description.get('updatedFields'),
        'removed_fields': update_description.get('removedFields'),
        'truncated_arrays': update_description.get('truncatedArrays'),
        'before_doc': before_doc,
        'full_doc': full_doc
    }
    return convert_for_json(payload)


def watch():
    db_name = mongo_config['db']
    user = mongo_config['user']
    pwd = mongo_config['pwd']
    host = mongo_config['host']
    db_url = f'mongodb://{user}:{pwd}@{host}/'

    client = MongoClient(db_url)
    db = client[db_name]

    pipeline = [
        {"$match": {
            'ns.coll': {'$in': watch_collections},
            'operationType': {'$in': ['insert', 'update', 'delete', 'replace']}
        }}
    ]
    with db.watch(full_document_before_change="whenAvailable", pipeline=pipeline) as stream:
        logger.info(f'{db_name} watch start')
        for change in stream:
            try:
                payload = make_payload(change)
                kafka_producer.send(payload)
                logger.info({'message': 'publish success', 'payload': payload})
            except Exception as e:
                logger.critical({'message': 'publish failed', 'error': e, 'change': str(change)})


# endregion


if __name__ == '__main__':
    watch()
