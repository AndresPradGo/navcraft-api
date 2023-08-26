"""
Db startup module

This module sets up the db character set and creates all the db tables and populates them.

Usage: 
- Import the set_up function and call it in main.py.

"""

import json
import sys

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError, TimeoutError

from auth.hasher import Hasher
import models
from utils.db import engine, Session
from utils import environ_variable_tools as environ


def __set_charracter_set() -> None:
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


def __create_tables() -> None:
    """
    This function creates all the db tables.

    Parameters: None

    Returns: None
    """

    models.Model.metadata.create_all(bind=engine)


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

    except (IntegrityError, TimeoutError, OperationalError) as e:
        print(f"Fatal Error! Could not create master user: {e}")
        sys.exit(1)


def __add_ruway_surfaces():
    """
    This function adds an initial list of runway surfaces.

    Parameters: None

    Returns: None
    """
    with open("config/runway_surfaces.json", "r") as json_file:
        surfaces = json.load(json_file)["surfaces"]

    try:
        with Session() as db:
            surfaces_in_db = [result.surface for result in db.query(models.RunwaySurface).filter(
                models.RunwaySurface.surface.in_(surfaces)).all()]
            surfaces_to_add = [models.RunwaySurface(
                surface=s
            ) for s in surfaces if s not in surfaces_in_db]

            db.add_all(surfaces_to_add)
            db.commit()

    except (IntegrityError, TimeoutError, OperationalError) as e:
        print(f"Error! could not add runway surfaces: {e}")


def __add_aerodrome_status():
    """
    This function adds an initial list of aerodrome status.

    Parameters: None

    Returns: None
    """
    with open("config/aerodrome_status.json", "r") as json_file:
        status = json.load(json_file)["status"]

    try:
        with Session() as db:
            status_in_db = [result.status for result in db.query(models.AerodromeStatus).filter(
                models.AerodromeStatus.status.in_(status)).all()]
            status_to_add = [models.AerodromeStatus(
                status=s
            ) for s in status if s not in status_in_db]

            db.add_all(status_to_add)
            db.commit()

    except (IntegrityError, TimeoutError, OperationalError) as e:
        print(f"Error! could not add aerodrome status: {e}")


def __populate_db():
    """
    This function populates the database with the minimum required data.

    Parameters: None

    Returns: None
    """
    __create_master_user()
    __add_ruway_surfaces()
    __add_aerodrome_status()


def set_up_database():
    """
    This function runs all the bd-setup functions in the correct order

    Parameters: None

    Returns: None
    """
    print("----- SETING UP DATABSE -----")
    __set_charracter_set()
    __create_tables()
    __populate_db()
