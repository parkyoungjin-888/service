import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton
from data_model_module.model_cashe_manager import ModelCacheManager
from mongodb_module.beanie_client_decorator import with_collection_client, collection_client_var
from fastapi_module.collection.collection_routes_model import *
from fastapi_module.collection.collection_routes_utils import api_log_decorator, convert_to_mongo_query

import uvicorn
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
import asyncio
from datetime import datetime
import gridfs
from pymongo import MongoClient
from bson import ObjectId
import time

import httpx


config = ConfigSingleton()
app_config = config.get_value('app')
collection_client_config = config.get_value('grpc-collection-manager')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.api', level=log_level)

router = APIRouter()
templates = Jinja2Templates(directory='templates')


# @router.post('/', response_model=DocId)
# @api_log_decorator(logger)
# async def insert_doc():
#     try:
#         res = {}
#         return JSONResponse(content=res, status_code=res['code'])
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse('main.html', {'request': request})


@router.get('/table', response_class=HTMLResponse)
async def image_list_table(request: Request):
    return templates.TemplateResponse("img_list_table.html", {'request': request})


@router.get('/video', response_class=HTMLResponse)
async def video_page(request: Request):
    return templates.TemplateResponse('video_streaming.html', {'request': request})


@router.websocket('/video/websocket')
async def video_stream(websocket: WebSocket):
    try:
        await websocket.accept()
        files = fs.find().sort("timestamp", 1).limit(100)
        for file in files:
            await websocket.send_bytes(file.read())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()



# @router.get('/image/{file_id}')
# async def get_image(file_id: str):
#     try:
#         file = fs.get(ObjectId(file_id))
#         return StreamingResponse(file, media_type='image/jpeg')
#     except gridfs.errors.NoFile:
#         raise HTTPException(status_code=404, detail='File not found')
#
#
# @router.get('/', response_class=HTMLResponse)
# async def home(request: Request):
#     return templates.TemplateResponse('main.html', {'request': request})
