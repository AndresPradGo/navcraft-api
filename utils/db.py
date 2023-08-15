"""
Sqlalchemy db tools

This module creates the tools to connect to the database. 
It defines the database engine, the databease sessions, 
and the get_db function to use as a database session 
inside the API endpoints.

Usage: 
- Import this module whenever you need to connect to the API's database.

"""

from os import environ

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

DB_NAME = "flight_planner_api_db"
DB_USER = environ.get('db_user')
DB_PASSWORD = environ.get('db_password')
DB_HOST = environ.get('db_host')
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DB_URL, echo=False)

session = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
)


def get_db() -> None:
    """
    This function initiates a database session to use inside the API endpoints

    Parameters: None

    Returns: None
    """

    database = session()
    try:
        yield database
    finally:
        database.close()
