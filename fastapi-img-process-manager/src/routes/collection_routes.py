import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton
from data_model_module import import_model
from mongodb_module.beanie_client_decorator import with_collection_client, collection_client_var
from src.routes.collection_routes_model import *
from src.routes.collection_routes_utils import api_log_decorator, convert_to_mongo_query


config = ConfigSingleton()
app_config = config.get_value('app')
data_model_name = config.get_value('data_model_name')
collection_client_config = config.get_value('grpc-collection-manager')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.api', level=log_level)

router = APIRouter()
data_model = import_model(data_model_name)


@router.post('/', response_model=DocId)
@api_log_decorator(logger)
@with_collection_client(collection_client_config, data_model)
async def insert_doc(doc: data_model):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='collection client not initialized.')

        res = await collection_client.insert_one(doc=doc.model_dump())

        return JSONResponse(content=res, status_code=res['code'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/list', response_model=DocIdList)
@api_log_decorator(logger)
@with_collection_client(collection_client_config, data_model)
async def insert_doc_list(doc_list: list[data_model]):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        res = await collection_client.insert_many(doc_list=[doc.model_dump() for doc in doc_list])

        return JSONResponse(content=res, status_code=res['code'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get('/tag')
@api_log_decorator(logger)
@with_collection_client(collection_client_config, data_model)
async def get_doc_tag(fields: list[str] = Query(...), query: list[str] = Query(None)):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        mongo_query = {}
        if query is not None:
            mongo_query = convert_to_mongo_query(query)

        res = await collection_client.get_tag(field_list=fields, query=mongo_query)
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])

        return JSONResponse(content=res['doc'], status_code=res['code'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/')
@api_log_decorator(logger)
@with_collection_client(collection_client_config, data_model)
async def get_doc(doc_id: str):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        res = await collection_client.get_one(doc_id=doc_id)
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])

        return JSONResponse(content=res['doc'], status_code=res['code'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/list', response_model=DocListResponse)
@api_log_decorator(logger)
@with_collection_client(collection_client_config, data_model)
async def get_doc_list(query: list[str] = Query(None), project_model_name: str = Query(None), 
                       sort: list[str] = Query(None), page_size: int = Query(None), page_num: int = Query(None)):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        mongo_query = {}
        if query is not None:
            mongo_query = convert_to_mongo_query(query)

        project_model = None
        if project_model_name is not None:
            project_model = import_model(project_model_name)

        res = await collection_client.get_many(query=mongo_query, project_model=project_model, sort=sort,
                                               page_size=page_size, page_num=page_num)

        return JSONResponse(content=res, status_code=res['code'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/', response_model=CountResponse)
@api_log_decorator(logger)
@with_collection_client(collection_client_config, data_model)
async def update_doc_many(doc_update_req: DocUpdateRequest):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        doc_update_req = doc_update_req.model_dump()
        query = {'_id': {'$in': doc_update_req['doc_id_list']}}
        res = await collection_client.update_many(query=query, set=doc_update_req['set'])

        return JSONResponse(content=res, status_code=res['code'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/', response_model=CountResponse)
@api_log_decorator(logger)
@with_collection_client(collection_client_config, data_model)
async def delete_doc_many(doc_id_list: DocIdList):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        query = {'_id': {'$in': doc_id_list.dict().get('doc_id_list')}}
        res = await collection_client.delete_many(query=query)

        return JSONResponse(content=res, status_code=res['code'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
