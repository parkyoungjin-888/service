from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from routers.table.schemas import TokenData
from config_module.config_singleton import ConfigSingleton


config = ConfigSingleton()
auth_config = config.get_value('auth')
SECRET_KEY = auth_config['secret_key']
ALGORITHM = auth_config['algorithm']
ACCESS_TOKEN_EXPIRE_MINUTES = auth_config['access_token_expire_min']


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(user_id=payload.get('user_id'), email=payload.get('email'))
    except JWTError:
        return None


if __name__ == '__main__':
    password_hash = get_password_hash('aaa')

    a = verify_password('aaa', password_hash)

    _token = create_access_token({'user_id': '123', 'a': 'aaa', 'b': 'bbb'})

    b = decode_access_token(_token)

    print('end')
