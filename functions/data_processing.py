"""
Useful Reusable Functions for Data Extaction, Checking and Processing.

Usage: 
- Import the required function and call it.
"""

from typing import List, Any

from fastapi import HTTPException, status
import pytz
from sqlalchemy import and_, not_
from sqlalchemy.orm import Session, Query

import models
from utils import common_responses


def clean_string(input_string: str) -> str:
    '''
    This functions takes a string and clens it by:
    - Removing leading and trailing white spaces.
    - Converts to lowercase and capitalizes first letter.
    - Replaces consecutive white spaces with a single space.

    Parameters:
    - input_string (str): string to be cleaned.

    Returns:
    str: cleaned string.
    '''

    return ' '.join([word.capitalize() for word in input_string.strip().split()])


async def get_user_id_from_email(email: str, db_session: Session):
    """
    This method queries the db for the user with the provided email, 
    and returns the user id.

    Parameters:
    - email (str): the user email.
    - db_session: an sqlalchemy db Session to query the database.

    Returns: 
    - int: the user id.

    Raises:
    - HTTPException (401): if it doesn't find a user with the provided email.
    - HTTPException (500): if there is a server error. 
    """
    user_id = db_session.query(models.User.id).filter(
        models.User.email == email).first()
    if not user_id:
        raise common_responses.invalid_credentials()

    return user_id[0]


def runways_are_unique(runways: List[Any]):
    """
    Checks if a list of runways is unique

    Parameters:
    - runways (list): a list of RunwayData instances

    Returns: 
    - bool: true is list is unique, and false otherwise
    """

    right_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position == "R"}
    left_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position == "L"}
    center_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position == "C"}
    none_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position is None}

    runways_with_position = right_runways | left_runways | center_runways
    all_runways = runways_with_position | none_runways

    runway_position_repeated = not len(right_runways) + len(left_runways)\
        + len(center_runways) + len(none_runways) == len(runways)

    runway_number_without_position_repeated = not len(runways_with_position)\
        + len(none_runways) == len(all_runways)

    if runway_position_repeated or\
            runway_number_without_position_repeated:
        return False

    return True


def check_performance_profile_and_permissions(
        db_session: Session,
        user_id: int,
        user_is_active_admin: bool,
        profile_id: int,
        auth_non_admin_get_model: bool = False
) -> Query[models.PerformanceProfile]:
    """
    Checks if user has permission to edit an aircraft performance profile.

    Parameters:
    - db_session (sqlalchemy Session): database session.
    - user_id (int): user id.
    - user_is_active_admin (bool): true if user is an active admin.
    - profile_id (int): performance profile id.

    Returns: 
    - Query[models.PerformanceProfile]: returns the performance profile query.
    """

    performance_profile_query = db_session.query(
        models.PerformanceProfile).filter_by(id=profile_id)
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with ID {profile_id} not found."
        )

    performance_for_model = performance_profile_query.first().aircraft_id is None

    if performance_for_model:
        if not user_is_active_admin and not auth_non_admin_get_model:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to edit this performance profile"
            )
    else:
        aircraft = db_session.query(models.Aircraft).filter_by(
            id=performance_profile_query.first().aircraft_id).first()

        if not aircraft.owner_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to edit this performance profile"
            )

    return performance_profile_query


def performance_profile_is_complete(profile_id: int, db_session: Session) -> bool:
    """
    This function checks if an aircraft performance profile meets 
    the minimum requirements to be complete, and if so, it returns True.
    """
    # Check table data
    table_data_modes_and_min_requireemnts = [
        {"model": models.TakeoffPerformance, "min_quantity": 2},
        {"model": models.LandingPerformance, "min_quantity": 2},
        {"model": models.ClimbPerformance, "min_quantity": 2},
        {"model": models.CruisePerformance, "min_quantity": 2},
        {"model": models.SeatRow, "min_quantity": 1},
        {"model": models.WeightBalanceProfile, "min_quantity": 1}
    ]

    for item in table_data_modes_and_min_requireemnts:
        data = db_session.query(item["model"]).filter(
            item["model"].performance_profile_id == profile_id
        ).all()
        if len(data) < item["min_quantity"]:
            return False

    # Check profile performance values
    profile_data = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.id == profile_id
    ).first()

    values = [
        profile_data.center_of_gravity_in,
        profile_data.empty_weight_lb,
        profile_data.max_ramp_weight_lb,
        profile_data.max_landing_weight_lb,
        profile_data.fuel_arm_in,
        profile_data.fuel_capacity_gallons
    ]
    there_are_null_values = sum(
        [1 for value in values if value is not None]) < len(values)
    if there_are_null_values:
        return False

    return True


def check_completeness_and_make_preferred_if_complete(profile_id: int, db_session: Session) -> None:
    """
    This function checks if the performance profile is complete and updates it accordingly.
    """
    performance_profile = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.id == profile_id
    ).first()
    if performance_profile.aircraft_id is not None:
        profile_is_complete = performance_profile_is_complete(
            profile_id=profile_id,
            db_session=db_session
        )

        if profile_is_complete:
            aircraft_preferred_profile = db_session.query(models.PerformanceProfile).filter(and_(
                models.PerformanceProfile.aircraft_id == performance_profile.aircraft_id,
                models.PerformanceProfile.is_preferred.is_(True),
                not_(models.PerformanceProfile.id == profile_id)
            )).first()

            make_preferred = aircraft_preferred_profile is None
        else:
            make_preferred = False

        db_session.query(models.PerformanceProfile).filter(
            models.PerformanceProfile.id == profile_id
        ).update({
            "is_complete": profile_is_complete,
            "is_preferred": make_preferred
        })

        db_session.commit()


def get_basic_flight_data_for_return(flight_id: int, db_session: Session, user_id: int):
    """
    This functions organizes basic flight data for returning to user.
    """
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    departure = db_session.query(models.Departure, models.Aerodrome)\
        .join(models.Aerodrome, models.Departure.aerodrome_id == models.Aerodrome.id)\
        .filter(models.Departure.flight_id == flight_id).first()

    arrival = db_session.query(models.Arrival, models.Aerodrome)\
        .join(models.Aerodrome, models.Arrival.aerodrome_id == models.Aerodrome.id)\
        .filter(models.Arrival.flight_id == flight_id).first()

    legs = db_session.query(models.Leg, models.FlightWaypoint, models.Waypoint)\
        .outerjoin(models.FlightWaypoint, models.Leg.id == models.FlightWaypoint.leg_id)\
        .outerjoin(models.Waypoint, models.FlightWaypoint.waypoint_id == models.Waypoint.id)\
        .filter(models.Leg.flight_id == flight_id).order_by(models.Leg.sequence).all()

    return {
        "id": flight.id,
        "departure_time": pytz.timezone('UTC').localize((flight.departure_time)),
        "aircraft_id": flight.aircraft_id,
        "departure_aerodrome_id": departure[1].id,
        "departure_aerodrome_is_private": departure[1].user_waypoint is not None,
        "arrival_aerodrome_id": arrival[1].id,
        "arrival_aerodrome_is_private": arrival[1].user_waypoint is not None,
        "bhp_percent": flight.bhp_percent,
        "reserve_fuel_hours": flight.reserve_fuel_hours,
        "contingency_fuel_hours": flight.contingency_fuel_hours,
        "fuel_on_board_gallons": flight.fuel_on_board_gallons,
        "legs": [{
            "id": leg.id,
            "sequence": leg.sequence,
            "waypoint": {
                "id": wp.id,
                "code": flight_wp.code,
                "name": flight_wp.name,
                "lat_degrees": wp.lat_degrees,
                "lat_minutes": wp.lat_minutes,
                "lat_seconds": wp.lat_seconds,
                "lat_direction": wp.lat_direction,
                "lon_degrees": wp.lon_degrees,
                "lon_minutes": wp.lon_minutes,
                "lon_seconds": wp.lon_seconds,
                "lon_direction": wp.lon_direction,
                "magnetic_variation": wp.magnetic_variation
            } if flight_wp is not None else None,
            "altitude_ft": leg.altitude_ft,
            "altimeter_inhg": leg.altimeter_inhg,
            "temperature_c": leg.temperature_c,
            "wind_magnitude_knot": leg.wind_magnitude_knot,
            "wind_direction": leg.wind_direction,
            "temperature_last_updated": pytz.timezone('UTC').localize((leg.temperature_last_updated))
            if leg.temperature_last_updated is not None else None,
            "wind_last_updated": pytz.timezone('UTC').localize((leg.wind_last_updated))
            if leg.wind_last_updated is not None else None,
            "altimeter_last_updated": pytz.timezone('UTC').localize((leg.altimeter_last_updated))
            if leg.altimeter_last_updated is not None else None
        } for leg, flight_wp, wp in legs]
    }
