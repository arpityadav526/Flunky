from sqlalchemy import create_engine
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base=declarative_base()

## CREATED THE DATABASE ##
DATABASE_URL="sqlite:///./flunky.db"

## CREATED THE ENGINE ##
engine=create_engine(DATABASE_URL, echo=True)

## CREATED THE SESSION CLASS FOR NOT USING THE ENGINE EVERYTIME
Session= sessionmaker(bind=engine)

## CREATED A BASE CLASS FOR ALL THE MODELS THAT ARE TO BE CREATED ##
class Base_class(Base):
    id=Column(Integer , primary_key=True )
    username= Column(String(20))
    email=Column(String(30))
    Hashed_password=Column(String(27))
    created_at=Column(DateTime, default=datetime.utcnow)
    title=Column(String(10))
    description=Column(String(100))
    is_completed=Column(Boolean)
    user_id=Column(ForeignKey('users.id'))

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
















