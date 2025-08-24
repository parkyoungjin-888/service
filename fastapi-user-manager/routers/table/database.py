from config_module.config_singleton import ConfigSingleton
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator


config = ConfigSingleton()
db_config = config.get_value('postgresql')
user = db_config['user']
pwd = db_config['pwd']
host = db_config['host']
port = db_config['port']
db = db_config['db']

DATABASE_URL = f'postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}'


engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
