import uvicorn
from fastapi import FastAPI

from config_module import init_config_and_logger


local_config_host = '192.168.0.104'
local_config_port = 21001
local_app_id = 'local-fastapi-user-manager'
config, logger = init_config_and_logger(local_config_host, local_config_port, local_app_id)


from routers.table.table_router import router as table_router


app_config = config.get_value('app')

app = FastAPI()
app.include_router(table_router, prefix=app_config['api_prefix'])


if __name__ == '__main__':
    logger.info({'message': 'server start', 'port': app_config['port']})
    uvicorn.run('app:app', host="0.0.0.0", port=app_config['port'])
