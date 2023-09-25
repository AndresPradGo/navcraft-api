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
from functions import navigation
from functions.aircraft_performance import get_landing_takeoff_data
from functions.data_processing import get_user_id_from_email

router = APIRouter(tags=["Flight Plan"])


async def get_nav_log_and_fuel_calculations(
    flight_id: int,
    db_session: Session,
    user_id: int
):
    """
    This reusable function prepares all the data to get the nav-log and fuel data,
    and returns the results.
    """
    # Get flight and check permissions
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

    # Get and return nav log and fuel data
    nav_log_data, fuel_data = navigation.calculate_nav_log(
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

    fuel_data["pre_takeoff_gallons"] = float(
        performance_profile.take_off_taxi_fuel_gallons)
    fuel_data["reserve_fuel_hours"] = float(flight.reserve_fuel_hours)
    fuel_data["contingency_fuel_hours"] = float(flight.contingency_fuel_hours)
    fuel_data["gallons_on_board"] = round(fuel_gallons, 2)

    return nav_log_data, fuel_data


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
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    nav_log_data, _ = await get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    return nav_log_data


@router.get(
    "/fuel-calculations/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.FuelCalculationResults
)
async def fuel_calculations(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Fuel Calculations Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - dict: dictionary with the fuel calculation results.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Get fuel data
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    _, fuel_data = await get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    average_gph = round(
        fuel_data["gallons_enroute"] / fuel_data["hours_enroute"], 1)

    # Return data
    return {
        "pre_takeoff_gallons": fuel_data["pre_takeoff_gallons"],
        "climb_gallons": fuel_data["climb_gallons"],
        "average_gph": average_gph,
        "enroute_fuel": {
            "hours": fuel_data["hours_enroute"],
            "gallons": round(fuel_data["hours_enroute"] * average_gph, 2)
        },
        "reserve_fuel": {
            "hours": fuel_data["reserve_fuel_hours"],
            "gallons": round(fuel_data["reserve_fuel_hours"] * average_gph, 2)
        },
        "contingency_fuel": {
            "hours": fuel_data["contingency_fuel_hours"],
            "gallons": round(fuel_data["contingency_fuel_hours"] * average_gph, 2)
        },
        "gallons_on_board": fuel_data["gallons_on_board"],
    }


@router.get(
    "/takeoff-landing-distances/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.TakeoffAndLandingDistances
)
async def takeoff_and_landing_distances(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Takeoff And Landing Distances Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - dict: dictionary with the takeoff and landing distance data.

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

    # Get takeoff and landing weight
    takeoff_weight = navigation.get_takeoff_weight(
        flight_id=flight_id,
        db_session=db_session
    )

    _, fuel_data = await get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    gallons_burned = float(sum([
        fuel_data["pre_takeoff_gallons"],
        fuel_data["climb_gallons"],
        fuel_data["gallons_enroute"]
    ]))

    fuel_type = db_session.query(models.FuelType).filter_by(
        id=performance_profile.fuel_type_id).first()
    fuel_density = float(fuel_type.density_lb_gal)

    landing_weight = takeoff_weight - gallons_burned * fuel_density

    # Loop for departure and arrival
    loop_parameters = {
        "departure": {
            "model": models.Departure,
            "weight": takeoff_weight
        },
        "arrival": {
            "model": models.Arrival,
            "weight": landing_weight
        }
    }
    takeoff_landing_result = {}
    for key, parameters in loop_parameters.items():
        # Get aerodrome and weather
        departure_arrival = db_session.query(parameters["model"], models.Aerodrome).join(
            models.Aerodrome,
            parameters["model"].aerodrome_id == models.Aerodrome.id
        ).filter(and_(
            parameters["model"].flight_id == flight_id,
            parameters["model"].aerodrome_id.isnot(None)
        )).first()
        if departure_arrival is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please make sure the flight has a departure and arrival aerodrome."
            )

        # Get runways
        runways = db_session.query(models.Runway).filter(
            models.Runway.aerodrome_id == departure_arrival[1].id
        ).all()

        # Loop through runways
        results_per_runway = []
        for runway in runways:
            pressure_alt = navigation.pressure_altitude_converter(
                altitude_ft=departure_arrival[1].elevation_ft,
                altimeter_inhg=float(departure_arrival[0].altimeter_inhg)
            )
            waypoint_id = departure_arrival[1].vfr_waypoint_id\
                if departure_arrival[1].vfr_waypoint_id is not None\
                else departure_arrival[1].user_waypoint_id

            waypoint = db_session.query(
                models.Waypoint).filter_by(id=waypoint_id).first()
            magnetic_variation = navigation.get_magnetic_variation_for_leg(
                from_waypoint=waypoint,
                to_waypoint=waypoint,
                db_session=db_session
            )

            wind_components = navigation.runway_wind_direction(
                wind_magnitude_knot=departure_arrival[0].wind_magnitude_knot,
                wind_direction_true=departure_arrival[0].wind_direction,
                runway_number=runway.number,
                magnetic_variation=magnetic_variation
            )

            # Get groundroll and obstacle clearance distances
            performance_data, performance_data_truncated_inputs = get_landing_takeoff_data(
                profile_id=performance_profile.id,
                is_takeoff=key == "departure",
                weight_lb=parameters["weight"],
                pressure_alt_ft=pressure_alt,
                temperature_c=departure_arrival[0].temperature_c,
                runway_surface_id=runway.surface_id,
                head_wind=wind_components["headwind"],
                db_session=db_session
            )

            # Organize runway data
            prefix = '0' if runway.number < 10 else ''
            suffix = runway.position if runway.position is not None else ''
            runway_length = runway.length_ft if key == "departure" else runway.landing_length_ft
            results_per_runway.append({
                "runway_id": runway.id,
                "runway": f"{prefix}{runway.number}{suffix}",
                "length_available_ft": runway_length,
                "interception_departure_length": runway.interception_departure_length_ft,
                "weight_lb": takeoff_weight if key == "departure" else landing_weight,
                "pressure_altitude_ft": pressure_alt,
                "truncated_pressure_altitude_ft": performance_data_truncated_inputs["pressure_alt_ft"],
                "temperature_c": departure_arrival[0].temperature_c,
                "truncated_temperature_c": performance_data_truncated_inputs["temperature_c"],
                "headwind_knot": wind_components["headwind"],
                "x_wind_knot": wind_components["crosswind"],
                "ground_roll_ft": performance_data["groundroll_ft"],
                "obstacle_clearance_ft": performance_data["obstacle_clearance_ft"],
            })

        takeoff_landing_result[key] = results_per_runway

    return takeoff_landing_result
