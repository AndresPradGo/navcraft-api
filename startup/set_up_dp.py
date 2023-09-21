"""
Db startup module

This module sets up the db character set and creates all the db tables and populates them.

Usage: 
- Import the set_up function and call it in main.py.

"""

import json
import os
import re
import sys

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError, TimeoutError as SqlalchemyTimeoutError

from auth.hasher import Hasher
import models
import schemas
from utils import environ_variable_tools as environ, csv_tools as csv
from utils.db import engine, Session
from functions.data_processing import clean_string

_PATH = "static_data/"


def _set_charracter_set() -> None:
    """
    This function sets up the database character set.
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
    """

    models.Model.metadata.create_all(bind=engine)


def _create_master_user():
    """
    This function creates the master user.
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


def _add_performance_profile_models():
    '''
    This function adds the initial performance profile models to the database.
    '''
    try:
        with Session() as db_session:
            db_is_populated = db_session.query(
                models.PerformanceProfile).first()
            if db_is_populated is None:
                # Loop through directories holding aircraft performance data
                directory_path = f"{_PATH}performance-profiles"
                for aircraft in os.listdir(directory_path):
                    aircraft_path = os.path.join(directory_path, aircraft)

                    # Load static data
                    if os.path.isdir(aircraft_path):
                        with open(f"{aircraft_path}/profile.json", mode="r", encoding="utf-8") as json_file:
                            profile_satic_data = json.load(json_file)
                        takeoff_static_data_list = csv.csv_to_list(
                            file_path=f"{aircraft_path}/takeoff_data.csv")
                        landing_static_data_list = csv.csv_to_list(
                            file_path=f"{aircraft_path}/landing_data.csv")
                        climb_static_data_list = csv.csv_to_list(
                            file_path=f"{aircraft_path}/climb_data.csv")
                        cruise_static_data_list = csv.csv_to_list(
                            file_path=f"{aircraft_path}/cruise_data.csv")

                        # Organize data models
                        profile_data = {
                            "base": schemas.OfficialPerformanceProfileData(
                                performance_profile_name=profile_satic_data["name"],
                                fuel_type_id=profile_satic_data["fuel_type_id"],
                                is_complete=profile_satic_data["is_complete"]
                            ),
                            "weight_balance": schemas.PerformanceProfileWeightBalanceData(**profile_satic_data),
                            "takeoff": schemas.RunwayDistanceAdjustmentPercentages(
                                percent_decrease_knot_headwind=profile_satic_data[
                                    "percent_decrease_takeoff_headwind_knot"
                                ],
                                percent_increase_knot_tailwind=profile_satic_data[
                                    "percent_increase_takeoff_tailwind_knot"
                                ],
                                percent_increase_runway_surfaces=[
                                    row for row in profile_satic_data["surface_performance_decreas_data"]
                                    if row["is_takeoff"]
                                ]
                            ),
                            "landing": schemas.RunwayDistanceAdjustmentPercentages(
                                percent_decrease_knot_headwind=profile_satic_data[
                                    "percent_decrease_landing_headwind_knot"
                                ],
                                percent_increase_knot_tailwind=profile_satic_data[
                                    "percent_increase_landing_tailwind_knot"
                                ],
                                percent_increase_runway_surfaces=[
                                    row for row in profile_satic_data["surface_performance_decreas_data"]
                                    if not row["is_takeoff"]
                                ]
                            ),
                            "climb": schemas.ClimbPerformanceAdjustments(**profile_satic_data)
                        }

                        baggage_compartments = [schemas.BaggageCompartmentData(
                            **row) for row in profile_satic_data["baggage_compartments"]]

                        seat_rows = [schemas.SeatRowData(
                            **row) for row in profile_satic_data["seat_rows"]]

                        fuel_tanks = [schemas.FuelTankData(
                            **row) for row in profile_satic_data["fuel_tanks"]]

                        weight_balance_profiles = [schemas.WeightBalanceData(
                            **wb_profile
                        ) for wb_profile in profile_satic_data["weight_balance_profiles"]]

                        takeoff_data = [schemas.TakeoffLandingPerformanceDataEntry(
                            weight_lb=float(row["weight_lb"]),
                            pressure_alt_ft=float(row["pressure_alt_ft"]),
                            temperature_c=float(row["temperature_c"]),
                            groundroll_ft=float(row["groundroll_ft"]),
                            obstacle_clearance_ft=float(
                                row["obstacle_clearance_ft"])
                        ) for row in takeoff_static_data_list]

                        landing_data = [schemas.TakeoffLandingPerformanceDataEntry(
                            **row)for row in landing_static_data_list]

                        climb_data = [schemas.ClimbPerformanceDataEntry(
                            **row) for row in climb_static_data_list]

                        cruise_data = [schemas.CruisePerformanceDataEntry(
                            **row) for row in cruise_static_data_list]

                        # Post performance profile
                        new_performance_profile = models.PerformanceProfile(
                            name=profile_data["base"].performance_profile_name,
                            is_complete=profile_data["base"].is_complete,
                            fuel_type_id=profile_data["base"].fuel_type_id,
                            center_of_gravity_in=profile_data["weight_balance"].center_of_gravity_in,
                            empty_weight_lb=profile_data["weight_balance"].empty_weight_lb,
                            max_ramp_weight_lb=profile_data["weight_balance"].max_ramp_weight_lb,
                            max_landing_weight_lb=profile_data["weight_balance"].max_landing_weight_lb,
                            baggage_allowance_lb=profile_data["weight_balance"].baggage_allowance_lb,
                            take_off_taxi_fuel_gallons=profile_data["climb"].take_off_taxi_fuel_gallons,
                            percent_increase_climb_temperature_c=profile_data[
                                "climb"].percent_increase_climb_temperature_c,
                            percent_decrease_takeoff_headwind_knot=profile_data[
                                "takeoff"].percent_decrease_knot_headwind,
                            percent_increase_takeoff_tailwind_knot=profile_data[
                                "takeoff"].percent_increase_knot_tailwind,
                            percent_decrease_landing_headwind_knot=profile_data[
                                "landing"].percent_decrease_knot_headwind,
                            percent_increase_landing_tailwind_knot=profile_data[
                                "landing"].percent_increase_knot_tailwind
                        )

                        db_session.add(new_performance_profile)
                        db_session.commit()
                        db_session.refresh(new_performance_profile)
                        performance_profile_id = new_performance_profile.id

                        # Add Weight & Balance profiles
                        for wb_profile in weight_balance_profiles:
                            new_wb_profile = models.WeightBalanceProfile(
                                performance_profile_id=performance_profile_id,
                                name=wb_profile.name,
                                max_take_off_weight_lb=wb_profile.max_take_off_weight_lb
                            )

                            db_session.add(new_wb_profile)
                            db_session.commit()
                            db_session.refresh(new_wb_profile)

                            new_wb_limits = [models.WeightBalanceLimit(
                                weight_balance_profile_id=new_wb_profile.id,
                                from_cg_in=limit.from_cg_in,
                                from_weight_lb=limit.from_weight_lb,
                                to_cg_in=limit.to_cg_in,
                                to_weight_lb=limit.to_weight_lb
                            ) for limit in wb_profile.limits]
                            db_session.add_all(new_wb_limits)
                            db_session.commit()

                        # Add baggage compartments
                        new_baggage_compartments = [models.BaggageCompartment(
                            **row.model_dump(),
                            performance_profile_id=performance_profile_id
                        ) for row in baggage_compartments]
                        db_session.add_all(new_baggage_compartments)

                        # Add seat rows
                        new_seat_rows = [models.SeatRow(
                            **row.model_dump(),
                            performance_profile_id=performance_profile_id
                        ) for row in seat_rows]
                        db_session.add_all(new_seat_rows)

                        # Add fuel tanks
                        new_fuel_tanks = [models.FuelTank(
                            **row.model_dump(),
                            performance_profile_id=performance_profile_id
                        ) for row in fuel_tanks]
                        db_session.add_all(new_fuel_tanks)

                        # Add runway surface adjustment values
                        new_takeoff_surface_adjustments = [models.SurfacePerformanceDecrease(
                            **row.model_dump(),
                            is_takeoff=True,
                            performance_profile_id=performance_profile_id
                        ) for row in profile_data["takeoff"].percent_increase_runway_surfaces]
                        new_landing_surface_adjustments = [models.SurfacePerformanceDecrease(
                            **row.model_dump(),
                            is_takeoff=False,
                            performance_profile_id=performance_profile_id
                        ) for row in profile_data["landing"].percent_increase_runway_surfaces]
                        db_session.add_all(
                            new_takeoff_surface_adjustments + new_landing_surface_adjustments
                        )

                        # Add takeoff performance data
                        new_takeoff_data = [models.TakeoffPerformance(
                            performance_profile_id=performance_profile_id,
                            **row.model_dump()
                        ) for row in takeoff_data]
                        db_session.add_all(new_takeoff_data)

                        # Add landing performance data
                        new_landing_data = [models.LandingPerformance(
                            performance_profile_id=performance_profile_id,
                            **row.model_dump()
                        ) for row in landing_data]
                        db_session.add_all(new_landing_data)

                        # Add climb performance data
                        new_climb_data = [models.ClimbPerformance(
                            performance_profile_id=performance_profile_id,
                            **row.model_dump()
                        ) for row in climb_data]
                        db_session.add_all(new_climb_data)

                        # Add cruise performance data
                        new_cruise_data = [models.CruisePerformance(
                            performance_profile_id=performance_profile_id,
                            **row.model_dump()
                        ) for row in cruise_data]
                        db_session.add_all(new_cruise_data)

                        db_session.commit()

    except (IntegrityError, SqlalchemyTimeoutError, OperationalError) as error:
        print(
            f"Error! could not add initial performance profile models: {error}")


def _populate_db():
    """
    This function populates the database with the minimum required data.
    """
    _create_master_user()
    _add_ruway_surfaces()
    _add_aerodrome_status()
    _add_vfr_waypoints()
    _add_aerodromes()
    _add_runways()
    _add_fuel_types()
    _add_performance_profile_models()


def set_up_database():
    """
    This function runs all the bd-setup functions in the correct order
    """
    print("----- SETING UP DATABSE -----")
    _set_charracter_set()
    _create_tables()
    _populate_db()
