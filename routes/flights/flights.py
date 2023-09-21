"""
FastAPI flights router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
import pytz
from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import (
    get_user_id_from_email,
    get_basic_flight_data_for_return
)
from functions import navigation

router = APIRouter(tags=["Flights"])


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.NewFlightReturn]
)
async def get_all_flights(
    flight_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Flights Endpoint.

    Parameters: 
    - flight_id (int): flight id.

    Returns: 
    - List: List of flights.

    Raise:
    - HTTPException (500): if there is a server error. 
    """
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    user_flights = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        or_(
            not_(flight_id),
            models.Flight.id == flight_id
        )
    )).all()

    flight_ids = [flight.id for flight in user_flights]

    return get_basic_flight_data_for_return(
        flight_ids=flight_ids,
        db_session=db_session,
        user_id=user_id
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.NewFlightReturn
)
async def post_new_flight(
    flight_data: schemas.NewFlightData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Flight Endpoint.

    Parameters: 
    - flight_data (dict): the flight data to be added.

    Returns: 
    - Dic: dictionary with the flight data and id.

    Raise:
    - HTTPException (400): if data is wrong.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Get user ID
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)

    # Check aircraft exists and is owned by user
    aircraft = db_session.query(models.PerformanceProfile, models.Aircraft).join(
        models.Aircraft,
        models.PerformanceProfile.aircraft_id == models.Aircraft.id
    ).filter(and_(
        models.Aircraft.id == flight_data.aircraft_id,
        models.Aircraft.owner_id == user_id,
        models.PerformanceProfile.is_preferred.is_(True),
        models.PerformanceProfile.is_complete.is_(True)
    )).first()
    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a valid aircraft ID, or complete the preferred performance profile."
        )

    # Check departure and arrival aerodromes exist
    a = models.Aerodrome
    u = models.UserWaypoint
    v = models.VfrWaypoint
    w = models.Waypoint

    departure = db_session.query(a, v, w)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id)\
        .join(w, v.waypoint_id == w.id)\
        .filter(and_(
            a.id == flight_data.departure_aerodrome_id,
            a.vfr_waypoint_id.isnot(None),
            not_(v.hidden)
        )).first()
    if departure is None:
        departure = db_session.query(a, u, w)\
            .join(u, a.user_waypoint_id == u.waypoint_id)\
            .join(w, u.waypoint_id == w.id)\
            .filter(and_(
                a.id == flight_data.departure_aerodrome_id,
                a.user_waypoint_id.isnot(None),
                u.creator_id == user_id
            )).first()
        if departure is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Departure aerodrome not found."
            )

    arrival = db_session.query(a, v, w)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id)\
        .join(w, v.waypoint_id == w.id)\
        .filter(and_(
            a.id == flight_data.arrival_aerodrome_id,
            a.vfr_waypoint_id.isnot(None),
            not_(v.hidden)
        )).first()
    if arrival is None:
        arrival = db_session.query(a, u, w)\
            .join(u, a.user_waypoint_id == u.waypoint_id)\
            .join(w, u.waypoint_id == w.id)\
            .filter(and_(
                a.id == flight_data.arrival_aerodrome_id,
                a.user_waypoint_id.isnot(None),
                u.creator_id == user_id
            )).first()
        if arrival is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arrival aerodrome not found."
            )

    # Check departure time is in the future
    if flight_data.departure_time <= pytz.timezone('UTC').localize(datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UTC estimated departure time, has to be in the future."
        )

    # Post new flight
    new_flight = models.Flight(
        pilot_id=user_id,
        departure_time=flight_data.departure_time,
        aircraft_id=aircraft[1].id
    )
    db_session.add(new_flight)
    db_session.commit()
    db_session.refresh(new_flight)
    new_flight_data = {**new_flight.__dict__}

    # Post fuel tanks
    print(aircraft[0].id)
    tank_ids = [tank.id for tank in db_session.query(models.FuelTank).filter_by(
        performance_profile_id=aircraft[0].id).all()]
    print(tank_ids)
    for tank_id in tank_ids:
        db_session.add(models.Fuel(
            flight_id=new_flight_data["id"],
            fuel_tank_id=tank_id
        ))

    # Post departure and arrival
    new_departure = models.Departure(
        flight_id=new_flight_data["id"],
        aerodrome_id=departure[0].id
    )
    db_session.add(new_departure)

    new_arrival = models.Arrival(
        flight_id=new_flight_data["id"],
        aerodrome_id=arrival[0].id
    )
    db_session.add(new_arrival)
    db_session.commit()

    # Post Leg
    magnetic_var = navigation.get_magnetic_variation_for_leg(
        from_waypoint=departure[2],
        to_waypoint=arrival[2],
        db_session=db_session
    )
    track_magnetic = departure[2].true_track_to_waypoint(
        arrival[2]) + magnetic_var
    easterly = track_magnetic >= 0 and track_magnetic < 180
    altitude_ft = navigation.round_altitude_to_odd_thousand_plus_500(
        min_altitude=max(
            departure[0].elevation_ft,
            arrival[0].elevation_ft
        ) + 2000
    ) if easterly else\
        navigation.round_altitude_to_even_thousand_plus_500(
            min_altitude=max(
                departure[0].elevation_ft,
                arrival[0].elevation_ft
            ) + 2000
    )
    new_leg = models.Leg(
        sequence=1,
        flight_id=new_flight_data["id"],
        altitude_ft=altitude_ft
    )
    db_session.add(new_leg)

    db_session.commit()
    db_session.refresh(new_leg)

    # Return flight data
    return get_basic_flight_data_for_return(
        flight_ids=[new_flight_data["id"]],
        db_session=db_session,
        user_id=user_id
    )[0]


@router.put(
    "/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.NewFlightReturn
)
async def edit_flight(
    flight_id: int,
    data: schemas.UpdateFlightData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Flight Endpoint.

    Parameters: 
    - flight_id (int): flight id.
    - data (dict): flight data.

    Returns: 
    - dict: flight data and id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Create flight query and check if flight exists
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight_query = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    ))

    if flight_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The flight you're trying to delete is not in the database."
        )

    # Edit flight

    flight_query.update(data.model_dump())

    return get_basic_flight_data_for_return(
        flight_ids=[flight_id],
        user_id=user_id,
        db_session=db_session
    )[0]


@router.put(
    "/change-aircraft/{flight_id}/{aircraft_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.NewFlightReturn
)
async def change_aircraft(
    flight_id: int,
    aircraft_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Change Aircraft Endpoint.

    Parameters: 
    - flight_id (int): flight id.
    - aircraft_id (int): aircraft id.

    Returns: 
    - dict: flight data and id.

    Raise:
    - HTTPException (400): if flight or aircraft doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get user ID
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)

    # Check if flight exists
    flight_query = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    ))

    if flight_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The flight you're trying to update."
        )

    # Check aircraft exists and is owned by user
    aircraft = db_session.query(models.PerformanceProfile, models.Aircraft).join(
        models.Aircraft,
        models.PerformanceProfile.aircraft_id == models.Aircraft.id
    ).filter(and_(
        models.Aircraft.id == aircraft_id,
        models.Aircraft.owner_id == user_id,
        models.PerformanceProfile.is_preferred.is_(True),
        models.PerformanceProfile.is_complete.is_(True)
    )).first()
    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a valid aircraft ID, or complete the preferred performance profile."
        )

    # Unload old aircraft
    old_aircraft_id = flight_query.first().aircraft_id
    if old_aircraft_id is not None:

        _ = db_session.query(models.PersonOnBoard).filter(
            models.PersonOnBoard.flight_id == flight_id).delete()
        _ = db_session.query(models.Baggage).filter(
            models.Baggage.flight_id == flight_id).delete()
        _ = db_session.query(models.Fuel).filter(
            models.Fuel.flight_id == flight_id).delete()

    # Change aircraft
    flight_query.update({"aircraft_id": aircraft_id})

    tank_ids = [tank.id for tank in db_session.query(models.FuelTank).filter_by(
        performance_profile_id=aircraft[0].id).all()]

    for tank_id in tank_ids:
        db_session.add(models.Fuel(
            flight_id=flight_id,
            fuel_tank_id=tank_id
        ))

    db_session.commit()

    return get_basic_flight_data_for_return(
        flight_ids=[flight_id],
        db_session=db_session,
        user_id=user_id
    )[0]


@router.put(
    "/departure-arrival/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.UpdateDepartureArrivalReturn
)
async def edit_departure_arrival(
    flight_id: int,
    is_departure: bool,
    data: schemas.UpdateDepartureArrivalData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Departure And Arrival Endpoint.

    Parameters: 
    - flight_id (int): flight id.
    - is_departure (bool): true is updating the departure, flase if the arrival.
    - data (dict): flight data.

    Returns: 
    - dict: flight data and id.

    Raise:
    - HTTPException (400): if flight or aerodrome doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if flight exists
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The flight you're trying to update."
        )

    # Check aerodrome exists
    a = models.Aerodrome
    u = models.UserWaypoint
    v = models.VfrWaypoint

    aerodrome = db_session.query(a, v)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id)\
        .filter(and_(
            a.id == data.aerodrome_id,
            a.vfr_waypoint_id.isnot(None),
            not_(v.hidden)
        )).first()
    if aerodrome is None:
        aerodrome = db_session.query(a, u)\
            .join(u, a.user_waypoint_id == u.waypoint_id)\
            .filter(and_(
                a.id == data.aerodrome_id,
                a.user_waypoint_id.isnot(None),
                u.creator_id == user_id
            )).first()
        if aerodrome is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Departure aerodrome not found."
            )

    # Edit and return departure/arrival
    model = models.Departure if is_departure else models.Arrival
    db_session.query(model).filter_by(
        flight_id=flight_id).update(data.model_dump())

    db_session.commit()

    updated_row = db_session.query(model).filter_by(
        flight_id=flight_id).first().__dict__

    updated_row["temperature_last_updated"] = pytz.timezone(
        'UTC').localize(updated_row["temperature_last_updated"])
    updated_row["wind_last_updated"] = pytz.timezone(
        'UTC').localize(updated_row["wind_last_updated"])
    updated_row["altimeter_last_updated"] = pytz.timezone(
        'UTC').localize(updated_row["altimeter_last_updated"])

    return updated_row


@router.delete("/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flight(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Flight.

    Parameters: 
    flight_id (int): flight id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    # Create flight query and check if flight exists
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight_query = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    ))

    if flight_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The flight you're trying to delete is not in the database."
        )

    # Get all waypoint IDs
    waypoint_ids = [
        waypoint.waypoint_id for _, waypoint in db_session
        .query(models.Leg, models.FlightWaypoint)
        .outerjoin(models.FlightWaypoint, models.Leg.id == models.FlightWaypoint.leg_id)
        .filter(models.Leg.flight_id == flight_id).all() if waypoint is not None
    ]

    # Delete flight and waypoints
    deleted_flight = flight_query.delete(synchronize_session=False)
    deleted_waypoints = db_session.query(models.Waypoint)\
        .filter(models.Waypoint.id.in_(waypoint_ids))\
        .delete(synchronize_session=False)
    if not deleted_flight or deleted_waypoints < len(waypoint_ids):
        raise common_responses.internal_server_error()

    db_session.commit()
