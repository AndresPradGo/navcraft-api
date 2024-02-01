"""
Useful Reusable Functions for Data Extaction, Checking and Processing.

Usage: 
- Import the required function and call it.
"""
from datetime import datetime
import math
from typing import List, Any

from fastapi import HTTPException, status
import pytz
from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session, Query

import models
from utils import common_responses
from functions.navigation import (
    find_nearby_aerodromes,
    find_aerodromes_within_radius,
    get_path_briefing_aerodromes
)


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
    list_by_space = [word.capitalize()
                     for word in input_string.strip().split()]
    new_list = []
    for sub_string in list_by_space:
        list_by_slash = [word.capitalize() for word in sub_string.split("/")]
        new_list.append('/'.join(list_by_slash))

    return ' '.join(new_list)


def get_user_id_from_email(email: str, db_session: Session):
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
    table_data_models_and_min_requireemnts = [
        {"model": models.TakeoffPerformance, "min_quantity": 2},
        {"model": models.LandingPerformance, "min_quantity": 2},
        {"model": models.ClimbPerformance, "min_quantity": 2},
        {"model": models.CruisePerformance, "min_quantity": 2},
        {"model": models.SeatRow, "min_quantity": 1},
        {"model": models.FuelTank, "min_quantity": 1},
        {"model": models.WeightBalanceProfile, "min_quantity": 1}
    ]

    for item in table_data_models_and_min_requireemnts:
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
        profile_data.max_landing_weight_lb
    ]
    there_are_null_values = sum(
        [1 for value in values if value is not None]) < len(values)
    if there_are_null_values:
        return False

    return True


def unload_aircraft(profile_id: int, db_session: Session):
    """
    This function deletes all persons on board baggages and fuel for 
    all flights using the performance profile passed as an argument.
    """
    # Get all flights
    profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id
    )).first()

    flights = db_session.query(models.Flight).filter_by(
        aircraft_id=profile.aircraft_id).all()

    # Unload all flights
    for flight in flights:
        _ = db_session.query(models.PersonOnBoard).filter(
            models.PersonOnBoard.flight_id == flight.id).delete()
        _ = db_session.query(models.Baggage).filter(
            models.Baggage.flight_id == flight.id).delete()
        _ = db_session.query(models.Fuel).filter(
            models.Fuel.flight_id == flight.id).delete()

    db_session.commit()


def create_empty_tanks(profile_id: int, db_session: Session):
    """
    This function created empty tanks for all flights 
    using the performance profile passed as an argument.
    """
    # Get all flights
    profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id
    )).first()

    flights = db_session.query(models.Flight).filter_by(
        aircraft_id=profile.aircraft_id).all()

    # Get tank ids
    tank_ids = [tank.id for tank in db_session.query(models.FuelTank).filter_by(
        performance_profile_id=profile_id).all()]

    # Create empty tanks
    for flight in flights:
        for tank_id in tank_ids:
            db_session.add(models.Fuel(
                flight_id=flight.id,
                fuel_tank_id=tank_id
            ))

    db_session.commit()


def check_completeness_and_make_preferred_if_complete(profile_id: int, db_session: Session) -> None:
    """
    This function checks if the performance profile is complete and updates it accordingly.
    """
    performance_profile = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.id == profile_id
    ).first()
    if performance_profile.aircraft_id is not None:
        profiles_was_preferred = performance_profile.is_preferred
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

        if profiles_was_preferred and not make_preferred:
            unload_aircraft(profile_id=profile_id, db_session=db_session)
        elif not profiles_was_preferred and make_preferred:
            create_empty_tanks(profile_id=profile_id, db_session=db_session)

        db_session.query(models.PerformanceProfile).filter(
            models.PerformanceProfile.id == profile_id
        ).update({
            "is_complete": profile_is_complete,
            "is_preferred": make_preferred
        })

        db_session.commit()


def get_basic_flight_data_for_return(flights: List[models.Flight], db_session: Session, user_id: int):
    """
    This functions organizes basic flight data for returning to user.
    """
    flight_list = []

    for flight in flights:
        flight_id = flight.id

        departure = db_session.query(models.Departure, models.Aerodrome, models.UserWaypoint)\
            .outerjoin(models.Aerodrome, models.Departure.aerodrome_id == models.Aerodrome.id)\
            .outerjoin(models.UserWaypoint, models.Aerodrome.user_waypoint_id == models.UserWaypoint.waypoint_id)\
            .filter(and_(
                models.Departure.flight_id == flight_id,
                or_(
                    models.Aerodrome.user_waypoint_id.is_(None),
                    models.UserWaypoint.creator_id == user_id
                )
            )).first()

        arrival = db_session.query(models.Arrival, models.Aerodrome, models.UserWaypoint)\
            .outerjoin(models.Aerodrome, models.Arrival.aerodrome_id == models.Aerodrome.id)\
            .outerjoin(models.UserWaypoint, models.Aerodrome.user_waypoint_id == models.UserWaypoint.waypoint_id)\
            .filter(and_(
                models.Arrival.flight_id == flight_id,
                or_(
                    models.Aerodrome.user_waypoint_id.is_(None),
                    models.UserWaypoint.creator_id == user_id
                )
            )).first()

        if arrival is None or departure is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Flight doesn't have a departure and/or arrival aerodrome."
            )

        legs = db_session.query(models.Leg, models.FlightWaypoint)\
            .join(models.FlightWaypoint, models.Leg.id == models.FlightWaypoint.leg_id)\
            .filter(models.Leg.flight_id == flight_id).order_by(models.Leg.sequence).all()

        flight_list.append({
            "id": flight.id,
            "departure_time": pytz.timezone('UTC').localize(flight.departure_time),
            "aircraft_id": flight.aircraft_id,
            "departure_aerodrome_id": departure[1].id if departure[1] is not None else None,
            "departure_aerodrome_is_private": departure[1].user_waypoint is not None
            if departure[1] is not None else None,
            "arrival_aerodrome_id": arrival[1].id if arrival[1] is not None else None,
            "arrival_aerodrome_is_private": arrival[1].user_waypoint is not None
            if arrival[1] is not None else None,
            "waypoints": [waypoint.code for _, waypoint in legs]
        })

    return flight_list


def get_extensive_flight_data_for_return(flight_ids: List[int], db_session: Session, user_id: int):
    """
    This functions organizes extensive flight data for returning to user.
    """
    flight_list = []

    flights = db_session.query(models.Flight).filter(and_(
        models.Flight.id.in_(flight_ids),
        models.Flight.pilot_id == user_id
    )).all()

    for flight in flights:
        flight_id = flight.id
        # Get data from DB
        departure = db_session.query(
            models.Departure,
            models.Aerodrome,
            models.AerodromeWeatherReport,
            models.UserWaypoint,
            models.VfrWaypoint,
            models.Waypoint
        )\
            .outerjoin(models.Aerodrome, models.Departure.aerodrome_id == models.Aerodrome.id)\
            .outerjoin(models.AerodromeWeatherReport, models.Departure.flight_id == models.AerodromeWeatherReport.departure_id)\
            .outerjoin(models.UserWaypoint, models.Aerodrome.user_waypoint_id == models.UserWaypoint.waypoint_id)\
            .outerjoin(models.VfrWaypoint, models.Aerodrome.vfr_waypoint_id == models.VfrWaypoint.waypoint_id)\
            .outerjoin(models.Waypoint, or_(
                models.Aerodrome.user_waypoint_id == models.Waypoint.id,
                models.Aerodrome.vfr_waypoint_id == models.Waypoint.id
            ))\
            .filter(and_(
                models.Departure.flight_id == flight_id,
                or_(
                    models.Aerodrome.user_waypoint_id.is_(None),
                    models.UserWaypoint.creator_id == user_id
                )
            )).first()

        arrival = db_session.query(
            models.Arrival,
            models.Aerodrome,
            models.AerodromeWeatherReport,
            models.UserWaypoint,
            models.VfrWaypoint,
            models.Waypoint
        )\
            .outerjoin(models.Aerodrome, models.Arrival.aerodrome_id == models.Aerodrome.id)\
            .outerjoin(models.AerodromeWeatherReport, models.Arrival.flight_id == models.AerodromeWeatherReport.arrival_id)\
            .outerjoin(models.UserWaypoint, models.Aerodrome.user_waypoint_id == models.UserWaypoint.waypoint_id)\
            .outerjoin(models.VfrWaypoint, models.Aerodrome.vfr_waypoint_id == models.VfrWaypoint.waypoint_id)\
            .outerjoin(models.Waypoint, or_(
                models.Aerodrome.user_waypoint_id == models.Waypoint.id,
                models.Aerodrome.vfr_waypoint_id == models.Waypoint.id
            ))\
            .filter(and_(
                models.Arrival.flight_id == flight_id,
                or_(
                    models.Aerodrome.user_waypoint_id.is_(None),
                    models.UserWaypoint.creator_id == user_id
                )
            )).first()

        if arrival is None or departure is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Flight doesn't have a departure and/or arrival aerodrome."
            )

        legs = db_session.query(models.Leg, models.FlightWaypoint, models.Waypoint, models.EnrouteWeatherReport)\
            .outerjoin(models.FlightWaypoint, models.Leg.id == models.FlightWaypoint.leg_id)\
            .outerjoin(models.Waypoint, models.FlightWaypoint.waypoint_id == models.Waypoint.id)\
            .outerjoin(models.EnrouteWeatherReport, models.Leg.id == models.EnrouteWeatherReport.id)\
            .filter(models.Leg.flight_id == flight_id).order_by(models.Leg.sequence).all()

        fuel_tanks = db_session.query(models.Fuel).filter_by(
            flight_id=flight_id).all()

        # Find if weather is official and when was it last updated
        dates = [{
            "official": departure[2].date if departure[2] is not None
            and flight.last_updated <= departure[2].date else None,
            "wind": departure[0].wind_last_updated
            if departure[0].wind_last_updated is not None
            and flight.last_updated <= departure[0].wind_last_updated
            else datetime(year=1, month=1, day=1),
            "temperature": departure[0].temperature_last_updated
            if departure[0].temperature_last_updated is not None
            and flight.last_updated <= departure[0].temperature_last_updated
            else datetime(year=1, month=1, day=1),
            "altimeter": departure[0].altimeter_last_updated
            if departure[0].altimeter_last_updated is not None
            and flight.last_updated <= departure[0].altimeter_last_updated
            else datetime(year=1, month=1, day=1)
        }] + [{
            "official": w.date if w is not None
            and flight.last_updated <= w.date else None,
            "wind": l.wind_last_updated
            if l.wind_last_updated is not None
            and flight.last_updated <= l.wind_last_updated
            else datetime(year=1, month=1, day=1),
            "temperature": l.temperature_last_updated
            if l.temperature_last_updated is not None
            and flight.last_updated <= l.temperature_last_updated
            else datetime(year=1, month=1, day=1),
            "altimeter": l.altimeter_last_updated
            if l.altimeter_last_updated is not None
            and flight.last_updated <= l.altimeter_last_updated
            else datetime(year=1, month=1, day=1)
        } for l, _, _, w in legs] + [
            {
                "official": arrival[2].date if arrival[2] is not None
                and flight.last_updated <= arrival[2].date else None,
                "wind": arrival[0].wind_last_updated
                if arrival[0].wind_last_updated is not None
                and flight.last_updated <= arrival[0].wind_last_updated
                else datetime(year=1, month=1, day=1),
                "temperature": arrival[0].temperature_last_updated
                if arrival[0].temperature_last_updated is not None
                and flight.last_updated <= arrival[0].temperature_last_updated
                else datetime(year=1, month=1, day=1),
                "altimeter": arrival[0].altimeter_last_updated
                if arrival[0].altimeter_last_updated is not None
                and flight.last_updated <= arrival[0].altimeter_last_updated
                else datetime(year=1, month=1, day=1)
            }
        ]
        all_weather_is_official = True
        weather_hours_from_etd = 0 if flight.departure_time >= datetime.utcnow() else -1
        for date in dates:
            wind_not_official = date["official"] is None\
                or date["wind"] > date["official"]
            temperature_not_official = date["official"] is None\
                or date["temperature"] > date["official"]
            altimeter_not_official = date["official"] is None\
                or date["altimeter"] > date["official"]

            any_weather_is_not_official = wind_not_official\
                or temperature_not_official\
                or altimeter_not_official

            all_weather_is_not_official = wind_not_official\
                and temperature_not_official\
                and altimeter_not_official

            if any_weather_is_not_official:
                all_weather_is_official = False

            if weather_hours_from_etd > -1:
                if all_weather_is_not_official:
                    date_list = [
                        date["wind"],
                        date["temperature"],
                        date["altimeter"]
                    ]
                    this_weather_time_from_etd = flight.departure_time - \
                        min(date_list, key=lambda x: x)
                else:
                    this_weather_time_from_etd = flight.departure_time - \
                        date["official"]

                weather_hours_from_etd = max([
                    round(this_weather_time_from_etd.total_seconds() / 3600, 0),
                    weather_hours_from_etd
                ])

        # Query all aerodromes for weather briefings/reports
        a = models.Aerodrome
        v = models.VfrWaypoint
        w = models.Waypoint
        departure_code = departure[4].code if departure[4] is not None else ""
        arrival_code = arrival[4].code if arrival[4] is not None else ""
        aerodromes_for_briefing = db_session.query(a, v, w)\
            .filter(and_(
                not_(v.hidden),
                a.user_waypoint_id.is_(None),
                not_(v.code == departure_code),
                not_(v.code == arrival_code)
            ))\
            .join(v, a.vfr_waypoint_id == v.waypoint_id)\
            .join(w, v.waypoint_id == w.id).all()

        weather_reports = ['TAF', 'METAR', 'Upper Wind']
        aerodromes_for_reports = {}
        aerodromes_for_reports_query = db_session.query(a, v, w)\
            .filter(and_(
                not_(v.hidden),
                a.user_waypoint_id.is_(None),
                or_(a.has_taf, a.has_metar, a.has_fds)
            ))\
            .join(v, a.vfr_waypoint_id == v.waypoint_id)\
            .join(w, v.waypoint_id == w.id).all()

        for weather_report in weather_reports:
            aerodromes_for_reports[weather_report] = [
                a for a in aerodromes_for_reports_query
                if (weather_report == "TAF" and a[0].has_taf)
                or (weather_report == "METAR" and a[0].has_metar)
                or (weather_report == "Upper Wind" and a[0].has_fds)
            ]

        # Get list of alternate options
        alternates = find_aerodromes_within_radius(
            aerodromes_query=aerodromes_for_briefing,
            lat=arrival[5].lat(),
            lon=arrival[5].lon(),
            radius=flight.alternate_radius_nm
        )
        aerodromes_for_briefing = [
            a for a in aerodromes_for_briefing
            if a[1].code not in {a["code"] for a in alternates}
        ]

        max_num_brief_aerodromes = math.floor(
            (45 - 2 - len(aerodromes_for_briefing)) / len(legs))

        # Organise list of flight legs
        legs_list = []
        previous_waypoint = departure[5]

        for (leg, flight_wp, wp, _) in legs:
            # Get weather report aerodromes for leg
            current_waypoint = wp if wp is not None else arrival[5]

            halfway_coordinates = previous_waypoint.find_halfway_coordinates(
                current_waypoint)

            upper_wind_aerodromes = find_nearby_aerodromes(
                aerodromes_query=aerodromes_for_reports["Upper Wind"],
                lat=halfway_coordinates[0],
                lon=halfway_coordinates[1],
                number=3
            )
            metar_aerodromes = find_nearby_aerodromes(
                aerodromes_query=aerodromes_for_reports["METAR"],
                lat=halfway_coordinates[0],
                lon=halfway_coordinates[1],
                number=3
            )

            # Get briefing aerodromes for leg
            briefing_aerodromes = find_aerodromes_within_radius(
                aerodromes_query=aerodromes_for_briefing,
                lat=previous_waypoint.lat(),
                lon=previous_waypoint.lon(),
                radius=flight.briefing_radius_nm,
            )
            aerodromes_for_briefing = [
                a for a in aerodromes_for_briefing
                if a[1].code not in {a["code"] for a in briefing_aerodromes}
            ]

            if previous_waypoint.great_arc_to_waypoint(current_waypoint) <= 150:
                path_boundaries = previous_waypoint.find_boundary_points(
                    to_waypoint=current_waypoint,
                    radius=flight.briefing_radius_nm
                )

                briefing_aerodromes += get_path_briefing_aerodromes(
                    aerodromes_query=aerodromes_for_briefing,
                    boundaries=path_boundaries,
                    reference=halfway_coordinates,
                    distance=flight.briefing_radius_nm
                )

            previous_waypoint = wp if wp is not None else arrival[5]
            aerodromes_for_briefing = [
                a for a in aerodromes_for_briefing
                if a[1].code not in {a["code"] for a in briefing_aerodromes}
            ]

            legs_list.append({
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
                    "magnetic_variation": wp.magnetic_variation,
                    "from_user_waypoint": flight_wp.from_user_waypoint,
                    "from_vfr_waypoint": flight_wp.from_vfr_waypoint,
                } if flight_wp is not None else None,
                "upper_wind_aerodromes": upper_wind_aerodromes,
                "metar_aerodromes": metar_aerodromes,
                "briefing_aerodromes": briefing_aerodromes,
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
            })

        # Append flight data
        flight_list.append({
            "id": flight.id,
            "departure_time": pytz.timezone('UTC').localize(flight.departure_time),
            "aircraft_id": flight.aircraft_id,
            "departure_aerodrome_id": departure[1].id if departure[1] is not None else None,
            "departure_aerodrome_is_private": departure[1].user_waypoint is not None
            if departure[1] is not None else None,
            "arrival_aerodrome_id": arrival[1].id if arrival[1] is not None else None,
            "arrival_aerodrome_is_private": arrival[1].user_waypoint is not None
            if arrival[1] is not None else None,
            "briefing_radius_nm": flight.briefing_radius_nm,
            "alternate_radius_nm": flight.alternate_radius_nm,
            "all_weather_is_official": all_weather_is_official,
            "weather_hours_from_etd": weather_hours_from_etd,
            "departure_weather": {
                "temperature_c": departure[0].temperature_c,
                "altimeter_inhg": departure[0].altimeter_inhg,
                "wind_direction": departure[0].wind_direction,
                "wind_magnitude_knot": departure[0].wind_magnitude_knot,
                "temperature_last_updated": pytz.timezone('UTC').localize(
                    (departure[0].temperature_last_updated)
                ) if departure[0].temperature_last_updated is not None else None,
                "wind_last_updated": pytz.timezone('UTC').localize(
                    (departure[0].wind_last_updated)
                ) if departure[0].wind_last_updated is not None else None,
                "altimeter_last_updated": pytz.timezone('UTC').localize(
                    (departure[0].altimeter_last_updated)
                ) if departure[0].altimeter_last_updated is not None else None,
            },
            "arrival_weather": {
                "temperature_c": arrival[0].temperature_c,
                "altimeter_inhg": arrival[0].altimeter_inhg,
                "wind_direction": arrival[0].wind_direction,
                "wind_magnitude_knot": arrival[0].wind_magnitude_knot,
                "temperature_last_updated": pytz.timezone('UTC').localize(
                    (arrival[0].temperature_last_updated)
                ) if arrival[0].temperature_last_updated is not None else None,
                "wind_last_updated": pytz.timezone('UTC').localize(
                    (arrival[0].wind_last_updated)
                ) if arrival[0].wind_last_updated is not None else None,
                "altimeter_last_updated": pytz.timezone('UTC').localize(
                    (arrival[0].altimeter_last_updated)
                ) if arrival[0].altimeter_last_updated is not None else None,
            },
            "bhp_percent": flight.bhp_percent,
            "added_enroute_time_hours": flight.added_enroute_time_hours,
            "reserve_fuel_hours": flight.reserve_fuel_hours,
            "contingency_fuel_hours": flight.contingency_fuel_hours,
            "fuel_on_board_gallons": sum((tank.gallons for tank in fuel_tanks)),
            "legs": legs_list,
            "departure_taf_aerodromes": find_nearby_aerodromes(
                aerodromes_query=aerodromes_for_reports["TAF"],
                lat=departure[5].lat(),
                lon=departure[5].lon(),
                number=3
            ),
            "departure_metar_aerodromes": find_nearby_aerodromes(
                aerodromes_query=aerodromes_for_reports["METAR"],
                lat=departure[5].lat(),
                lon=departure[5].lon(),
                number=3
            ),
            "arrival_taf_aerodromes": find_nearby_aerodromes(
                aerodromes_query=aerodromes_for_reports["TAF"],
                lat=arrival[5].lat(),
                lon=arrival[5].lon(),
                number=3
            ),
            "arrival_metar_aerodromes": find_nearby_aerodromes(
                aerodromes_query=aerodromes_for_reports["METAR"],
                lat=arrival[5].lat(),
                lon=arrival[5].lon(),
                number=3
            ),
            "alternates": alternates
        })

    return flight_list


def flight_has_origin_and_destination(flight_id: int, db_session: Session) -> bool:
    """
    This function checks that a particular flight 
    has departure and arrival aerodromes.
    """

    departure_arrival_models = [
        models.Departure,
        models.Arrival
    ]
    for model in departure_arrival_models:
        departure_arrival = db_session.query(
            model,
            models.Aerodrome
        ).join(
            models.Aerodrome,
            model.aerodrome_id == models.Aerodrome.id
        ).filter(and_(
            model.flight_id == flight_id,
            model.aerodrome_id.isnot(None)
        )).first()

        if departure_arrival is None:
            return False

    return True
