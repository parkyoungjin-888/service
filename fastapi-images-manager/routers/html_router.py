import os
import base64
import mimetypes
from typing import Optional
from collections import OrderedDict
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from botocore.exceptions import ClientError

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


config = ConfigSingleton()
app_config = config.get_value('app')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.api', level=log_level)


def create_router(s3_client):
    router = APIRouter()
    templates = Jinja2Templates(directory='templates')

    @router.get('/home', response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse('main.html', {'request': request})

    @router.get('/table', response_class=HTMLResponse)
    async def render_table(request: Request):
        table_fields = OrderedDict([
            ('_id', 'ID'),
            ('device_id', 'Device'),
            ('name', 'Name'),
            ('event_datetime', 'Event Time'),
        ])

        project_model_name = 'ProjectImage'
        sort = '-event_datetime'
        page_size = 10
        get_list_url = f'/images/list?project_model_name={project_model_name}&sort={sort}&page_size={page_size}'

        tag_fields = ['device_id']
        get_tag_url = f'/images/tag?fields={'&fields='.join(tag_fields)}'
        blank_tag_texts = {'device_id': 'All Device'}

        return templates.TemplateResponse('list_table.html', {
            'request': request,
            'get_list_url': get_list_url,
            'get_tag_url': get_tag_url,
            'table_fields': table_fields,
            'field_order': list(table_fields.keys()),
            'tag_fields': tag_fields,
            'blank_tag_texts': blank_tag_texts
        })

    @router.get('/display', response_class=HTMLResponse)
    async def display_image(img_path: Optional[str] = Query(None)):
        if not img_path:
            return HTMLResponse(
                "<p style='text-align:center;margin-top:20px;'>No Image</p>",
                status_code=200
            )

        try:
            obj = s3_client.get_object(Bucket='images', Key=img_path)
            content = obj['Body'].read()

            mime_type, _ = mimetypes.guess_type(img_path)
            mime_type = mime_type or 'application/octet-stream'

            if not mime_type.startswith("image/"):
                return HTMLResponse(
                    f"<p style='text-align:center;margin-top:20px;'>이미지 파일이 아닙니다: {img_path}</p>",
                    status_code=200
                )
            # base64로 인라인 이미지 표시
            b64_image = base64.b64encode(content).decode("utf-8")
            return HTMLResponse(
                f"""
                <div style="text-align:center;margin-top:10px;">
                    <img src="data:{mime_type};base64,{b64_image}" alt="이미지" style="max-width:100%;max-height:95vh;">
                </div>
                """,
                status_code=200
            )
        except ClientError as e:
            return HTMLResponse(
                "<p style='text-align:center;margin-top:20px;color:red;'>이미지를 불러올 수 없습니다.</p>",
                status_code=200
            )

    return router
