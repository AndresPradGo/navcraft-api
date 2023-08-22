"""
Db startup module

This module sets up the db character set and creates all the db tables.

Usage: 
- Import the set_charracter_set and create_tables functions into the main.py module. 
  Call the set_charracter_set function first.

"""

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import models
from utils.db import engine


def set_charracter_set() -> None:
    """
    This function sets up the database character set.

    Parameters: None

    Returns: None
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SET NAMES utf8mb4;"))
            connection.execute(text("SET character_set_client = utf8mb4;"))
    except OperationalError as e:
        print(f"Error setting character set and collation: {e}")


def create_tables() -> None:
    """
    This function creates all the db tables.

    Parameters: None

    Returns: None
    """

    models.Model.metadata.create_all(bind=engine)
