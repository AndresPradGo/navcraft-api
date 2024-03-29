"""
Sqlalchemy db tools

This module creates the tools to connect to the database. 
It defines the database engine, the databease sessions, 
and the get_db function to use as a database session 
inside the API endpoints.

Usage: 
- Import this module whenever you need to connect to the API's database.

"""


from sqlalchemy import create_engine
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    InterfaceError,
    TimeoutError as SqlalchemyTimeoutError
)
from sqlalchemy.orm import sessionmaker

from utils import environ_variable_tools as environ

DB_NAME = environ.get('db_name')
DB_USER = environ.get('db_user')
DB_PASSWORD = environ.get('db_password')
DB_HOST = environ.get('db_host')
DB_PORT = environ.get('db_port')
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DB_URL, echo=False)

Session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """
    This generator function initiates a database session to use inside the API endpoints.

    Parameters: None
    """

    database = Session()
    try:
        yield database

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError, InterfaceError):
        database.rollback()
        raise
    finally:
        database.close()
