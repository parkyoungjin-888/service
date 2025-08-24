from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from routers.table import database, models, auth
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/token")


async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(database.get_session)):
    token_data = auth.decode_access_token(token)
    if not token_data or not token_data.email:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(models.User).
        where(models.User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
