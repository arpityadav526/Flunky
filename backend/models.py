from backend.database import Base_class
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm  import relationship


Base = declarative_base()  # Empty parent class

class User(Base):
    __tablename__ = 'users'
    # User fields only
    tasks = relationship("Tasks", back_populates="owner")

class Task(Base):
    __tablename__ = 'tasks'
    # Task fields only
owner=relationship("User", back_populates="tasks")
