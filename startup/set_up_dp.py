"""
Db startup module

This module sets up the db character set and creates all the db tables and populates them.

Usage: 
- Import the set_up function and call it in main.py.

"""

import re
import sys

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError, TimeoutError as SqlalchemyTimeoutError

from auth.hasher import Hasher
import models
import schemas
from utils import environ_variable_tools as environ, csv_tools as csv
from utils.db import engine, Session
from utils.functions import clean_string

_PATH = "static_data/"


def _set_charracter_set() -> None:
    """
    This function sets up the database character set.

    Parameters: None

    Returns: None
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SET NAMES utf8mb4;"))
            connection.execute(text("SET character_set_client = utf8mb4;"))
    except OperationalError as error:
        print(f"Error setting character set and collation: {error}")


def _create_tables() -> None:
    """
    This function creates all the db tables.

    Parameters: None

    Returns: None
    """

    models.Model.metadata.create_all(bind=engine)


def _create_master_user():
    """
    This function creates the master user.

    Parameters: None

    Returns: None
    """

    try:
        user_email = environ.get("master_user_email")
        with Session() as db_session:
            user_exists = db_session.query(models.User).filter(
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
                db_session.add(user)
                db_session.commit()

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Fatal Error! Could not create master user: {error}")
        sys.exit(1)


def _add_ruway_surfaces():
    """
    This function adds an initial list of runway surfaces.

    Parameters: None

    Returns: None
    """
    pattern = r"^[-A-Za-z ']*$"

    surfaces = [
        clean_string(s["surface"]) for s in csv.csv_to_list(
            file_path=f"{_PATH}runway_surfaces.csv"
        ) if re.match(pattern, s["surface"]) is not None
    ]

    try:
        with Session() as db_session:
            db_is_populated = db_session.query(models.RunwaySurface).first()
            if db_is_populated is None:
                surfaces_to_add = [models.RunwaySurface(
                    surface=s
                ) for s in surfaces]

                db_session.add_all(surfaces_to_add)
                db_session.commit()

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Error! could not add runway surfaces: {error}")


def _add_aerodrome_status():
    """
    This function adds an initial list of aerodrome status.

    Parameters: None

    Returns: None
    """

    pattern = r"^[-A-Za-z ]*$"

    status = [
        clean_string(s["status"]) for s in csv.csv_to_list(
            file_path=f"{_PATH}aerodrome_status.csv"
        ) if re.match(pattern, s["status"]) is not None
    ]

    try:
        with Session() as db_session:
            db_is_populated = db_session.query(models.AerodromeStatus).first()
            if db_is_populated is None:
                status_to_add = [models.AerodromeStatus(
                    status=s
                ) for s in status]

                db_session.add_all(status_to_add)
                db_session.commit()

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Error! could not add aerodrome status: {error}")


def _add_vfr_waypoints():
    """
    This function adds an initial list of vfr_waypoint.

    Parameters: None

    Returns: None
    """

    data_to_add = [schemas.VfrWaypointData(
        **w) for w in csv.csv_to_list(file_path=f"{_PATH}vfr_waypoints.csv")]

    try:
        with Session() as db_session:
            db_is_populated = db_session.query(models.VfrWaypoint).first()

            if db_is_populated is None:
                user_id = db_session.query(models.User.id).first()[0]

                for waypoint in data_to_add:
                    new_waypoint = models.Waypoint(
                        lat_degrees=waypoint.lat_degrees,
                        lat_minutes=waypoint.lat_minutes,
                        lat_seconds=waypoint.lat_seconds,
                        lat_direction=waypoint.lat_direction,
                        lon_degrees=waypoint.lon_degrees,
                        lon_minutes=waypoint.lon_minutes,
                        lon_seconds=waypoint.lon_seconds,
                        lon_direction=waypoint.lon_direction,
                        magnetic_variation=waypoint.magnetic_variation,
                    )
                    db_session.add(new_waypoint)
                    db_session.commit()
                    db_session.refresh(new_waypoint)

                    new_vfr_waypoint = models.VfrWaypoint(
                        waypoint_id=new_waypoint.id,
                        code=waypoint.code,
                        name=waypoint.name,
                        hidden=waypoint.hidden,
                        creator_id=user_id
                    )
                    db_session.add(new_vfr_waypoint)
                    db_session.commit()

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Error! could not add vfr waypoints: {error}")


def _add_aerodromes():
    """
    This function adds an initial list of aerodromes.

    Parameters: None

    Returns: None
    """

    data_to_add = [schemas.RegisteredAerodromeData(
        **a, status=a["status_id"]) for a in csv.csv_to_list(file_path=f"{_PATH}aerodromes.csv")]

    try:
        with Session() as db_session:
            db_is_populated = db_session.query(models.Aerodrome).first()

            if db_is_populated is None:
                user_id = db_session.query(models.User.id).first()[0]

                for aerodrome in data_to_add:
                    new_waypoint = models.Waypoint(
                        lat_degrees=aerodrome.lat_degrees,
                        lat_minutes=aerodrome.lat_minutes,
                        lat_seconds=aerodrome.lat_seconds,
                        lat_direction=aerodrome.lat_direction,
                        lon_degrees=aerodrome.lon_degrees,
                        lon_minutes=aerodrome.lon_minutes,
                        lon_seconds=aerodrome.lon_seconds,
                        lon_direction=aerodrome.lon_direction,
                        magnetic_variation=aerodrome.magnetic_variation,
                    )
                    db_session.add(new_waypoint)
                    db_session.commit()
                    db_session.refresh(new_waypoint)

                    new_vfr_waypoint = models.VfrWaypoint(
                        waypoint_id=new_waypoint.id,
                        code=aerodrome.code,
                        name=aerodrome.name,
                        hidden=aerodrome.hidden,
                        creator_id=user_id
                    )
                    db_session.add(new_vfr_waypoint)

                    new_aerodrome = models.Aerodrome(
                        id=new_waypoint.id,
                        vfr_waypoint_id=new_waypoint.id,
                        has_taf=aerodrome.has_taf,
                        has_metar=aerodrome.has_metar,
                        has_fds=aerodrome.has_fds,
                        elevation_ft=aerodrome.elevation_ft,
                        status_id=aerodrome.status
                    )
                    db_session.add(new_aerodrome)

                    db_session.commit()

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Error! could not add aerodromes: {error}")


def _add_runways():
    """
    This function adds an initial list of runways.

    Parameters: None

    Returns: None
    """

    data_to_add = [schemas.RunwayData(**{
        "aerodrome_id": r["aerodrome_id"],
        "number": r["number"],
        "length_ft": r["length_ft"],
        "surface_id": r["surface_id"]
    }) if r["position"] == "" else schemas.RunwayData(**{
        "aerodrome_id": r["aerodrome_id"],
        "number": r["number"],
        "position": r["position"],
        "length_ft": r["length_ft"],
        "surface_id": r["surface_id"]
    }) for r in csv.csv_to_list(file_path=f"{_PATH}runways.csv")]

    try:
        with Session() as db_session:
            db_is_populated = db_session.query(models.Runway).first()

            if db_is_populated is None:
                for runway in data_to_add:
                    new_runway = models.Runway(
                        aerodrome_id=runway.aerodrome_id,
                        number=runway.number,
                        position=runway.position,
                        length_ft=runway.length_ft,
                        surface_id=runway.surface_id
                    )
                    db_session.add(new_runway)
                db_session.commit()

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Error! could not add runways: {error}")


def _add_fuel_types():
    """
    This function adds an initial list of fuel types.

    Parameters: None

    Returns: None
    """
    data_to_add = [schemas.FuelTypeData(**{
        "name": f["name"],
        "density_lb_gal": f["density_lb_gal"]
    }) for f in csv.csv_to_list(file_path=f"{_PATH}fuel_types.csv")]

    try:
        with Session() as db_session:
            db_is_populated = db_session.query(models.FuelType).first()

            if db_is_populated is None:
                for fuel_type in data_to_add:
                    new_fuel_type = models.FuelType(
                        name=fuel_type.name,
                        density_lb_gal=fuel_type.density_lb_gal,
                    )
                    db_session.add(new_fuel_type)
                db_session.commit()
    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Error! could not add fuel types: {error}")


def _add_aircraft_manufacturers():
    """
    This function adds an initial list of aircraft manufacturers.

    Parameters: None

    Returns: None
    """
    data_to_add = [schemas.AircraftMakeData(**{
        "name": f["name"]
    }) for f in csv.csv_to_list(file_path=f"{_PATH}manufacturers.csv")]

    try:
        with Session() as db_session:
            db_is_populated = db_session.query(models.AircraftMake).first()

            if db_is_populated is None:
                for manufacturer in data_to_add:
                    new_manufacturer = models.AircraftMake(
                        name=manufacturer.name
                    )
                    db_session.add(new_manufacturer)
                db_session.commit()
    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(f"Error! could not add fuel types: {error}")


def _populate_db():
    """
    This function populates the database with the minimum required data.

    Parameters: None

    Returns: None
    """
    _create_master_user()
    _add_ruway_surfaces()
    _add_aerodrome_status()
    _add_vfr_waypoints()
    _add_aerodromes()
    _add_runways()
    _add_fuel_types()
    _add_aircraft_manufacturers()


def set_up_database():
    """
    This function runs all the bd-setup functions in the correct order

    Parameters: None

    Returns: None
    """
    print("----- SETING UP DATABSE -----")
    _set_charracter_set()
    _create_tables()
    _populate_db()
