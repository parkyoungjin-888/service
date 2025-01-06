import grpc
from bson import ObjectId
from google.protobuf.json_format import MessageToDict
from pydantic import BaseModel, ValidationError
from functools import wraps
from google.protobuf import struct_pb2
from pymongo import UpdateMany

from mongodb_module.proto import collection_pb2 as pb2
from mongodb_module.proto import collection_pb2_grpc
from data_model_module.beanie_data_model.model_importer import import_model


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


class CollectionServer(collection_pb2_grpc.CollectionServerServicer):
    def __init__(self, data_model, module_name: str):
        self.module_name = module_name
        self.collection_model = data_model

    def _get_query_request_data(self, request):
        if request.HasField('project_model'):
            project_model = import_model(self.module_name, request.project_model)
        else:
            project_model = None

        query_request_dict = {
            'query': MessageToDict(request.query),
            'project_model': project_model,
            'sort': list(request.sort) if len(request.sort) > 0 else None,
            'page_size': request.page_size if request.HasField('page_size') else None,
            'page_num': request.page_num if request.HasField('page_num') else None
        }
        return query_request_dict

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
        query_request_data = self._get_query_request_data(request)
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
