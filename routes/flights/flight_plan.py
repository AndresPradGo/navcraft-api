"""
FastAPI navigation log router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils.db import get_db
from functions.data_processing import get_user_id_from_email
from functions import navigation

router = APIRouter(tags=["Flight Plan"])


@router.get(
    "/nav-log/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.NavigationLogLegResults]
)
async def navigation_log(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Navigation Log Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - list: list of dictionaries with the nav-log data per leg.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Get flight and check permissions
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )
    # Get performance_profile
    aircraft = db_session.query(
        models.PerformanceProfile,
        models.Aircraft
    ).join(
        models.Aircraft,
        models.PerformanceProfile.aircraft_id == models.Aircraft.id
    ).filter(and_(
        models.Aircraft.id == flight.aircraft_id,
        models.PerformanceProfile.is_preferred.is_(True),
        models.PerformanceProfile.is_complete.is_(True)
    )).first()

    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aircraft does not have a preferred performance profile."
        )

    performance_profile = aircraft[0]

    # Get departure and arrival waypoints
    departure_arrival_models = [
        models.Departure,
        models.Arrival
    ]
    departure_arrival_waypoints = []
    aerodromes_weather = []
    for departure_arrival_model in departure_arrival_models:
        departure_arrival = db_session.query(departure_arrival_model, models.Aerodrome).join(
            models.Aerodrome,
            departure_arrival_model.aerodrome_id == models.Aerodrome.id
        ).filter(and_(
            departure_arrival_model.flight_id == flight_id,
            departure_arrival_model.aerodrome_id.isnot(None)
        )).first()
        if departure_arrival is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please make sure the flight has a departure and arrival aerodrome."
            )
        aerodromes_weather.append(departure_arrival)
        if departure_arrival[1].vfr_waypoint_id is not None:
            departure_arrival_waypoint = db_session.query(
                models.VfrWaypoint,
                models.Waypoint
            ).join(
                models.Waypoint,
                models.VfrWaypoint.waypoint_id == models.Waypoint.id
            ).filter(models.VfrWaypoint.waypoint_id == departure_arrival[1].vfr_waypoint_id).first()
        else:
            departure_arrival_waypoint = db_session.query(
                models.UserWaypoint,
                models.Waypoint
            ).join(
                models.Waypoint,
                models.UserWaypoint.waypoint_id == models.Waypoint.id
            ).filter(models.UserWaypoint.waypoint_id == departure_arrival[1].user_waypoint_id).first()

        departure_arrival_waypoints.append(departure_arrival_waypoint)

    # Get legs and flight waypoints
    legs_query_results = db_session.query(
        models.Leg,
        models.FlightWaypoint,
        models.Waypoint
    ).outerjoin(
        models.FlightWaypoint,
        models.Leg.id == models.FlightWaypoint.leg_id
    ).outerjoin(
        models.Waypoint,
        models.FlightWaypoint.waypoint_id == models.Waypoint.id
    ).filter(
        models.Leg.flight_id == flight_id
    ).order_by(models.Leg.sequence).all()

    legs = [leg for leg, _, _ in legs_query_results]

    # Organize waypoint data
    waypoints = [waypoint for _, _,
                 waypoint in legs_query_results if waypoint is not None]
    waypoints.insert(0, departure_arrival_waypoints[0][1])
    waypoints.append(departure_arrival_waypoints[1][1])

    waypoint_names_codes = [{
        "name": waypoint.name,
        "code": waypoint.code
    } for _, waypoint, _ in legs_query_results if waypoint is not None]
    waypoint_names_codes.insert(0, {
        "name": departure_arrival_waypoints[0][0].name,
        "code": departure_arrival_waypoints[0][0].code
    })
    waypoint_names_codes.append({
        "name": departure_arrival_waypoints[1][0].name,
        "code": departure_arrival_waypoints[1][0].code
    })

    pressure_alt_at_departure = navigation.pressure_altitude_converter(
        altitude_ft=aerodromes_weather[0][1].elevation_ft,
        altimeter_inhg=float(aerodromes_weather[0][0].altimeter_inhg)
    )

    # Get fuel density
    fuel_type = db_session.query(models.FuelType).filter_by(
        id=performance_profile.fuel_type_id).first()
    fuel_density = float(fuel_type.density_lb_gal)

    # Get total fuel gallons
    fuel_tanks = db_session.query(models.Fuel).filter(
        models.Fuel.flight_id == flight_id
    ).all()

    fuel_gallons = float(sum([fuel_tank.gallons for fuel_tank in fuel_tanks]))

    # Get and return nav log data
    nav_log_data, _ = navigation.calculate_nav_log(
        profile_id=performance_profile.id,
        legs=legs,
        waypoints=waypoints,
        waypoint_names_codes=waypoint_names_codes,
        pressure_altitude_at_departure_aerodrome=pressure_alt_at_departure,
        takeoff_weight=navigation.get_takeoff_weight(
            flight_id=flight_id,
            db_session=db_session
        ),
        bhp_percent=flight.bhp_percent,
        fuel_density=fuel_density,
        fuel_gallons=fuel_gallons,
        db_session=db_session
    )

    return nav_log_data
