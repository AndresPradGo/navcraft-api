"""
Db startup module

This module creates the database.

Usage: 
- Import the create_database function into the main.py module and call it. 

"""
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, TimeoutError

from utils import environ_variable_tools as environ

DB_NAME = environ.get('db_name')
DB_USER = environ.get('db_user')
DB_PASSWORD = environ.get('db_password')
DB_HOST = environ.get('db_host')
TEMP_DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/mysql"


def create_database() -> None:
    """
    This function creates the database if it doesn't exist.

    Parameters: None

    Returns: None
    """

    print("------ CREATING DATABSE ------")
    temp_engine = create_engine(TEMP_DB_URL)

    try:
        with temp_engine.connect() as connection:
            connection.execute(
                text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
    except (TimeoutError, OperationalError) as e:
        print(f"Fatal Error! Could not create database: {e}")
        sys.exit(1)
