import os
import grpc
import asyncio
import importlib
from bson import ObjectId
from concurrent import futures
from google.protobuf.json_format import MessageToDict
from pydantic import ValidationError
from functools import wraps
from google.protobuf import struct_pb2
from pymongo import UpdateMany

from config_module.config_singleton import ConfigSingleton
from mongodb_module.proto import collection_pb2 as pb2
from mongodb_module.proto import collection_pb2_grpc
from mongodb_module.beanie_control import BaseDocument, BeanieControl
# from mongodb_module.beanie_data_model.user_model import User, ProjectUser


# region ############################## config section ##############################

local_config_host = '192.168.0.105'
local_config_port = 31001
local_app_id = 'service-collection-manager-001'

config = ConfigSingleton()
config_host = os.environ.get('CONFIG_HOST') if os.environ.get('CONFIG_HOST') else local_config_host
config_port = int(os.environ.get('CONFIG_PORT')) if os.environ.get('CONFIG_PORT') else local_config_port

app_id = os.environ.get('APP_ID') if os.environ.get('APP_ID') else local_app_id
config.load_config(host=config_host, port=config_port, app_id=app_id)
print(f'config load data, host : {config_host}, port : {config_port}, app_id : {app_id}')

# endregion

# region ############################## service define section ##############################


def grpc_server_error_handler(response):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, request, context):
            try:
                return await func(self, request, context)
            except ValidationError as ve:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f'ValidationError: {str(ve)}')
                return response
            except Exception as e:
                context.set_code(grpc.StatusCode.UNKNOWN)
                context.set_details(f'Unexpected Error: {str(e)}')
                return response
        return wrapper
    return decorator


def get_query_request_data(request, model_module):
    project_model = import_model(request.project_model, model_module) if request.HasField('project_model') else None
    query_request_dict = {
        'query': MessageToDict(request.query),
        'project_model': project_model,
        'sort': list(request.sort) if len(request.sort) > 0 else None,
        'page_size': request.page_size if request.HasField('page_size') else None,
        'page_num': request.page_num if request.HasField('page_num') else None
    }
    return query_request_dict


class CollectionServer(collection_pb2_grpc.CollectionServerServicer):
    def __init__(self, collection_model: type[BaseDocument]):
        self.collection_model = collection_model

    @grpc_server_error_handler(pb2.IdResponse())
    async def InsertOne(self, request, context):
        doc = MessageToDict(request.doc)
        valid_doc = self.collection_model(**doc)
        res = await self.collection_model.insert_one(valid_doc)

        response = pb2.IdResponse()
        response.doc_id = str(res.id)
        response.code = 200
        return response

    @grpc_server_error_handler(pb2.IdListResponse())
    async def InsertMany(self, request, context):
        doc_list = [MessageToDict(doc, preserving_proto_field_name=True) for doc in request.doc_list]
        valid_doc_list = [self.collection_model(**doc) for doc in doc_list]
        res = await self.collection_model.insert_many(valid_doc_list)

        response = pb2.IdListResponse()
        response.doc_id_list.extend([str(doc_id) for doc_id in res.inserted_ids])
        response.code = 200
        return response

    @grpc_server_error_handler(pb2.DocResponse())
    async def GetTag(self, request, context):
        field_list = request.field_list
        query = MessageToDict(request.query) if request.HasField('query') else None
        response = pb2.DocResponse()
        doc_struct = struct_pb2.Struct()
        for field in field_list:
            res = await self.collection_model.distinct(key=field, filter=query)
            res = [{'value': str(r), 'type': type(r).__name__} for r in res]
            doc_struct.update({field: res})

        response.doc = doc_struct
        response.code = 200
        return response

    @grpc_server_error_handler(pb2.DocResponse())
    async def GetOne(self, request, context):
        doc_id = ObjectId(request.doc_id)
        res = await self.collection_model.find_one({'_id': doc_id})

        response = pb2.DocResponse()
        if res is None:
            response.code = 400
            response.message = f'doc is not found, doc_id : {doc_id}'
            return response

        res = res.model_dump(by_alias=True)
        if '_id' in res:
            res['_id'] = str(res['_id'])
        response.doc = res
        response.code = 200
        return response

    @grpc_server_error_handler(pb2.DocListResponse())
    async def GetMany(self, request, context):
        query_request_data = get_query_request_data(request, data_model_module)
        res = await self.collection_model.find_with_paginate(**query_request_data)

        response = pb2.DocListResponse()
        for doc in res['doc_list']:
            doc_struct = struct_pb2.Struct()
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            doc_struct.update(doc)
            response.doc_list.append(doc_struct)

        response.total_count = res['total_count']
        response.code = 200
        return response

    @grpc_server_error_handler(pb2.CountResponse())
    async def UpdateMany(self, request, context):
        update_req_list = request.update_request_list

        bulk_write_req = []
        for update_req in update_req_list:
            req = {'filter': MessageToDict(update_req.query, preserving_proto_field_name=True), 'update': {}}
            if update_req.HasField('set'):
                req['update'].update({'$set': MessageToDict(update_req.set, preserving_proto_field_name=True)})
            if update_req.HasField('unset'):
                req['update'].update({'$unset': MessageToDict(update_req.unset, preserving_proto_field_name=True)})
            if update_req.HasField('push'):
                req['update'].update({'$push': MessageToDict(update_req.push, preserving_proto_field_name=True)})
            if update_req.HasField('array_filter'):
                req['array_filters'] = [MessageToDict(update_req.array_filter, preserving_proto_field_name=True)]
            if update_req.HasField('upsert'):
                req['upsert'] = update_req.upsert
            if req['update'] == {}:
                continue
            bulk_write_req.append(UpdateMany(**req))
        res = await self.collection_model.get_motor_collection().bulk_write(bulk_write_req)

        response = pb2.CountResponse()
        response.count = res.modified_count
        response.code = 200
        return response

    @grpc_server_error_handler(pb2.CountResponse())
    async def DeleteMany(self, request, context):
        query = MessageToDict(request.query)
        res = await self.collection_model.delete_many(query)

        response = pb2.CountResponse()
        response.count = res
        response.code = 200
        return response

    @grpc_server_error_handler(pb2.DocListResponse())
    async def Aggregate(self, request, context):
        pipeline = [MessageToDict(p, preserving_proto_field_name=True) for p in request.pipeline]
        res = await self.collection_model.aggregate(pipeline).to_list()

        response = pb2.DocListResponse()
        for doc in res:
            doc_struct = struct_pb2.Struct()
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            doc_struct.update(doc)
            response.doc_list.append(doc_struct)

        response.total_count = len(res)
        response.code = 200
        return response


def import_model(class_name, module_name):
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


async def serve():
    model = import_model(model_name, data_model_module)

    mongo_config = config.get_value('mongo')
    beanie_control = BeanieControl(**mongo_config)
    await beanie_control.init([model])

    app_config = config.get_value('app')

    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    collection_pb2_grpc.add_CollectionServerServicer_to_server(CollectionServer(model), server)
    server.add_insecure_port(f'[::]:{app_config['port']}')
    await server.start()

    print(f'{app_config['name']} serve start : 0.0.0.0:{app_config['port']}')

    await server.wait_for_termination()

# endregion


if __name__ == '__main__':
    data_model_module = 'mongodb_module.beanie_data_model.user_model'
    model_name = 'User'

    asyncio.run(serve())
