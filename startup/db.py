"""
Db startup module

This module initiates the database, creating all the db tables.

Usage: 
- Import the create_tables function into the main.py module, and call it with no parameters.

"""

import models
from utils.db import engine


def create_tables() -> None:
    """
    This function creates all the db tables.

    Parameters: None

    Returns: None
    """

    models.Model.metadata.create_all(bind=engine)
