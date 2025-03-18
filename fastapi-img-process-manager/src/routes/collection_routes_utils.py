import time
import json
import urllib.parse
from functools import wraps
from pydantic import BaseModel


def dump_kwargs(kwargs: dict) -> dict:
    serialized_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, list):
            serialized_kwargs[key] = [v.model_dump() if isinstance(v, BaseModel) else v for v in value]
        elif isinstance(value, BaseModel):
            serialized_kwargs[key] = value.model_dump()
        else:
            serialized_kwargs[key] = value
    return serialized_kwargs


def dump_response(response, res_max_size: int = 1000):
    response_body_dict = json.loads(response.body.decode('utf-8'))
    if not len(str(response.body)) > res_max_size:
        return response_body_dict
    else:
        return str(response_body_dict)[:res_max_size] + ' ...'


def api_log_decorator(logger, res_max_size: int = 1000):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                response = await func(*args, **kwargs)
                tact_time = time.time() - start_time
                logger.info({
                    'function': func.__name__,
                    'args': [a.model_dump() if isinstance(a, BaseModel) else a for a in args],
                    'kwargs': dump_kwargs(kwargs),
                    'status_code': response.status_code,
                    'response': dump_response(response, res_max_size),
                    'tact_time': round(tact_time, 4),
                    'message': 'success'
                })
                return response
            except Exception as e:
                tact_time = time.time() - start_time
                logger.error({
                    'function': func.__name__,
                    'args': [a.model_dump() if isinstance(a, BaseModel) else a for a in args],
                    'kwargs': dump_kwargs(kwargs),
                    'tact_time': round(tact_time, 4),
                    'message': e,
                })
                raise e

        return wrapper

    return decorator


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
