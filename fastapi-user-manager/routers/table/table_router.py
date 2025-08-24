import os
from fastapi import APIRouter, Depends, HTTPException

from config_module.config_singleton import ConfigSingleton
from utils_module.logger import LoggerSingleton

config = ConfigSingleton()
app_config = config.get_value('app')

log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = LoggerSingleton.get_logger(f'{app_config["name"]}.api', level=log_level)


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from routers.table import schemas, models
from routers.table.database import engine, get_session
from routers.table.auth import get_password_hash, verify_password, create_access_token
from routers.table.dependencies import get_current_user
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.on_event('startup')
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


@router.post('/', response_model=schemas.UserRead)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_session)):
    hashed_pw = get_password_hash(user.password)
    new_user = models.User(name=user.name, email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get('/{user_id}', response_model=schemas.UserRead)
async def read_user(user_id: int, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get('/me', response_model=schemas.UserRead)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(models.User).where(models.User.id == int(form_data.username)))
    user = result.scalar_one_or_none()
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail='Incorrect username or password')

    token_payload = {'user_id': user.id, 'email': user.email}
    token = create_access_token(token_payload)
    return {'access_token': token, 'token_type': 'bearer'}
