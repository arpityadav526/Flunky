from fastapi import Depends , HTTPException , status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, session
from passlib.context import CryptContext
from jose import jwt ,JWTError
from datetime import datetime , timedelta
from backend.database import  get_db
from backend.models import User

pwd_context=CryptContext(schemes=["bcrypt"] , deprecated="auto")
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="login")


def hash_password(password: str)-> str:
    hashed_password=pwd_context.hash(password)
    return hashed_password


def verify_password(password: str, hashed_password: str)-> bool:
        return pwd_context.verify(password , hashed_password)



SECRET_KEY="9cd1a4d415c33ed344298b14ea82c18616a37b48717bd6b46e4099fde1b9d2b6"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTE=30


## {"name": "april"} sample data for the function below

def create_access_token(data: dict)-> str:
    to_encode=data.copy()
    expire_time=datetime.utcnow()+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTE)
    to_encode.update({"exp": expire_time})
    token_str=jwt.encode(to_encode,SECRET_KEY, algorithm=ALGORITHM)
    return token_str


def verify_token(token_str: str)->str:
    payload=jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
    username=payload.get("sub")
    try:
        if username is None:
         raise HTTPException(status_code=401 , detail="unprocessable_content",headers={"WWW-Authenticate": "Bearer"})
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="unauthorized", headers={"WWW-Authenticate": "Bearer"})



def get_current_user(token_str: str=Depends(oauth2_scheme), db: session=Depends(get_db))->User:
    username=verify_token(token_str)

    user = db.query(User).filter(User.username==username).first()

    if user is None:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user







