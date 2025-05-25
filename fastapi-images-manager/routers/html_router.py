import os
from collections import OrderedDict
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton


config = ConfigSingleton()
app_config = config.get_value('app')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.api', level=log_level)

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


# @router.get('/display', response_class=HTMLResponse)
# async def display_image(img_path: str = ""):
#     print('here')
#     return f"""
#     <html>
#     <body>
#         <img src="{img_path}" style="max-width:100%; max-height:100%;">
#     </body>
#     </html>
#     """
