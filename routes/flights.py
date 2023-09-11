"""
FastAPI flights router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from datetime import datetime
import re
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
import pytz
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from utils.functions import clean_string, get_user_id_from_email

router = APIRouter(tags=["Flights"])


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.FlightStatusReturn]
)
async def get_all_flight_status(
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Flight Status Endpoint.

    Returns: 
    - list: list of flight status.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    return [
        status.__dict__ for status in db_session.query(models.FlightStatus).all()
    ]


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
    - HTTPException (400): if flight status already exists, or it
      contains characters other than letters, hyphen and white space.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get user ID
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)

    # Check aircraft exists and is owned by user
    aircraft = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == flight_data.aircraft_id,
        models.Aircraft.owner_id == user_id
    )).first()
    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid aircraft ID."
        )

    # Check departure and arrival aerodromes exist
    a = models.Aerodrome
    u = models.UserWaypoint
    v = models.VfrWaypoint

    departure = db_session.query(a, u, v)\
        .outerjoin(u, a.user_waypoint_id == u.waypoint_id)\
        .outerjoin(v, a.vfr_waypoint_id == v.waypoint_id)\
        .filter(and_(
            a.id == flight_data.departure_aerodrome_id,
            or_(
                a.vfr_waypoint_id.isnot(None),
                u.creator_id == user_id
            )
        )).first()
    if departure is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Departure aerodrome not found."
        )

    arrival = db_session.query(a, u, v)\
        .outerjoin(u, a.user_waypoint_id == u.waypoint_id)\
        .outerjoin(v, a.vfr_waypoint_id == v.waypoint_id)\
        .filter(and_(
            a.id == flight_data.arrival_aerodrome_id,
            or_(
                a.vfr_waypoint_id.isnot(None),
                u.creator_id == user_id
            )
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
        aircraft_id=aircraft.id,
        status_id=1
    )
    db_session.add(new_flight)
    db_session.commit()
    db_session.refresh(new_flight)
    new_flight_data = {**new_flight.__dict__}

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

    # Return flight data
    return {
        "id": new_flight_data["id"],
        "departure_time": flight_data.departure_time,
        "aircraft_id": aircraft.id,
        "departure_aerodrome_id": departure[0].id,
        "departure_aerodrome_is_private": departure[0].user_waypoint is not None,
        "arrival_aerodrome_id": arrival[0].id,
        "arrival_aerodrome_is_private": arrival[0].user_waypoint is not None

    }


@router.post(
    "/status",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FlightStatusReturn
)
async def post_new_flight_status(
    flight_status: str,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Flight Status Endpoint.

    Parameters: 
    - flight_status (str): the flight status to be added.

    Returns: 
    - Dic: dictionary with the flight status and id.

    Raise:
    - HTTPException (400): if flight status already exists, or it
      contains characters other than letters, hyphen and white space.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    pattern = r'^[-A-Za-z ]*$'
    status_matches_pattern = re.match(pattern, flight_status) is not None
    if not status_matches_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use only letters, hyphens, and spaces in the flight status."
        )

    clean_status = clean_string(flight_status)

    already_exists = db_session.query(models.FlightStatus).filter_by(
        status=clean_status).first()
    if already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight status already exists."
        )

    new_flight_status = models.FlightStatus(status=clean_status)
    db_session.add(new_flight_status)
    db_session.commit()
    db_session.refresh(new_flight_status)

    return new_flight_status


@router.delete("/status/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aerodrome_status(
    status_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Flight Status.

    Parameters: 
    status_id (int): status id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    status_query = db_session.query(
        models.FlightStatus).filter_by(id=status_id)

    if not status_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The flight status you're trying to delete is not in the database."
        )

    deleted = status_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()
