import urllib.parse
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from config_module.config_singleton import ConfigSingleton
from data_model_module import import_model
from mongodb_module.beanie_client_decorator import with_collection_client, collection_client_var


config = ConfigSingleton()
data_model_name = config.get_value('data_model_name')
collection_client_config = config.get_value('grpc-collection-manager')

router = APIRouter()
data_model = import_model(data_model_name)


class DocId(BaseModel):
    doc_id: str
    
    
class DocIdList(BaseModel):
    doc_id_list: list[str]


class DocListResponse(BaseModel):
    doc_list: list[dict]
    total_count: int


class DocUpdateRequest(BaseModel):
    doc_id_list: list[str]
    set: dict


class CountResponse(BaseModel):
    count: int


def convert_to_mongo_query(query: list[str]):
    mongo_query = {}
    for q in query:
        q = urllib.parse.unquote(q)
        if '>=' in q:
            field, value = q.split('>=')
            mongo_query[field] = {'$gte': float(value)}
        elif '<=' in q:
            field, value = q.split('<=')
            mongo_query[field] = {'$lte': float(value)}
        elif '>' in q:
            field, value = q.split('>')
            mongo_query[field] = {'$gt': float(value)}
        elif '<' in q:
            field, value = q.split('<')
            mongo_query[field] = {'$lt': float(value)}
        elif '~' in q:
            field, value = q.split('~')
            mongo_query[field] = {'$regex': value}
        elif '!=' in q:
            field, value = q.split('!=')
            if value.startswith('[') and value.endswith(']'):
                value = {'$nin': [v.strip(' []') for v in value.split(',')]}
            else:
                value = {'$ne': value}
            mongo_query[field] = value
        elif '=' in q:
            field, value = q.split('=')
            if value.startswith('[') and value.endswith(']'):
                value = {'$in': [v.strip(' []') for v in value.split(',')]}
            mongo_query[field] = value
        else:
            raise ValueError(f'Unsupported query format: {q}')
    return mongo_query


@router.post('/', response_model=DocId)
@with_collection_client(collection_client_config, data_model)
async def insert_doc(doc: data_model):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='collection client not initialized.')

        res = await collection_client.insert_one(doc=doc.model_dump())
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])
        
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/list', response_model=DocIdList)
@with_collection_client(collection_client_config, data_model)
async def insert_doc_list(doc_list: list[data_model]):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        res = await collection_client.insert_many(doc_list=[doc.model_dump() for doc in doc_list])
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get('/tag')
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
        
        return res['doc']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/')
@with_collection_client(collection_client_config, data_model)
async def get_doc(doc_id: str):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        res = await collection_client.get_one(doc_id=doc_id)
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])

        return res['doc']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/list', response_model=DocListResponse)
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
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/', response_model=CountResponse)
@with_collection_client(collection_client_config, data_model)
async def update_doc_many(doc_update_req: DocUpdateRequest):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        doc_update_req = doc_update_req.model_dump()
        query = {'_id': {'$in': doc_update_req['doc_id_list']}}
        res = await collection_client.update_many(query=query, set=doc_update_req['set'])
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/', response_model=CountResponse)
@with_collection_client(collection_client_config, data_model)
async def delete_doc_many(doc_id_list: DocIdList):
    try:
        collection_client = collection_client_var.get(None)
        if collection_client is None:
            raise HTTPException(status_code=500, detail='Collection client not initialized.')

        query = {'_id': {'$in': doc_id_list.dict().get('doc_id_list')}}
        res = await collection_client.delete_many(query=query)
        if res['code'] // 100 != 2:
            return JSONResponse(content=res, status_code=res['code'])

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
