"""
Populate Database module

This module populates the database with the required data to start.

Usage: 
- Import the module and call all functions individualy in main.py.

"""

import asyncio
import sys

from sqlalchemy.exc import IntegrityError

from auth.hasher import Hasher
import models
from queries import user_queries
from utils import environ_variable_tools as environ
from utils.db import Session


def __create_master_user():
    """
    This function creates the master user.

    Parameters: None

    Returns: None
    """

    try:
        user_email = environ.get("master_user_email")
        with Session() as db:
            user_exists = db.query(models.User).filter(
                models.User.email == user_email).first()
            if not user_exists:
                user = models.User(
                    email=user_email,
                    name=environ.get("master_user_name"),
                    weight_lb=environ.get("master_user_weight"),
                    password=Hasher.bcrypt(
                        environ.get("master_user_password")),
                    is_admin=True,
                    is_master=True
                )
                db.add(user)
                db.commit()

    except IntegrityError as e:
        print(f"Fatal Error! Could not create master user: {e}")
        sys.exit(1)


def populate_db():
    __create_master_user()
