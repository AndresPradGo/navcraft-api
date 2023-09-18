"""
FastAPI flights router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from datetime import datetime

from fastapi import APIRouter, Depends, status, HTTPException
import pytz
from sqlalchemy import and_, not_
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
    aircraft = db_session.query(models.Aircraft, models.PerformanceProfile)\
        .join(models.PerformanceProfile,
              models.Aircraft.id == models.PerformanceProfile.aircraft_id)\
        .filter(and_(
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
        aircraft_id=aircraft[0].id
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
        flight_id=new_flight_data["id"],
        db_session=db_session,
        user_id=user_id
    )


@router.post(
    "/person-on-board/{flight_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PersonOnBoardReturn
)
async def add_person_on_board(
    flight_id: int,
    data: schemas.PersonOnBoardData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Add Person On Board Endpoint.

    Parameters: 
    - flight_id (int): flight id.
    - data (dict): name and weight of personand seat row.

    Returns: 
    - dict: person on board data and id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exist
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile
    ).join(
        models.Aircraft,
        models.Flight.aircraft_id == models.Aircraft.id
    ).join(
        models.PerformanceProfile,
        models.Aircraft.id == models.PerformanceProfile.aircraft_id
    ).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Check seat-row exists
    seat_row = db_session.query(models.SeatRow).filter(and_(
        models.SeatRow.id == data.seat_row_id,
        models.SeatRow.performance_profile_id == flight[2].id
    )).first()

    if seat_row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seat row not found."
        )
    # Process data
    if data.name is not None:
        new_person_on_board = models.PersonOnBoard(
            flight_id=flight_id,
            seat_row_id=data.seat_row_id,
            name=data.name,
            weight_lb=data.weight_lb
        )
    elif data.is_me is not None:
        user = db_session.query(models.User).filter_by(id=user_id).first()
        new_person_on_board = models.PersonOnBoard(
            flight_id=flight_id,
            seat_row_id=data.seat_row_id,
            name=user.name,
            weight_lb=user.weight_lb
        )
    else:
        passenger = db_session.query(models.PassengerProfile).filter(and_(
            models.PassengerProfile.creator_id == user_id,
            models.PassengerProfile.id == data.passenger_profile_id
        )).first()
        if passenger is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passenger profile not found."
            )
        new_person_on_board = models.PersonOnBoard(
            flight_id=flight_id,
            seat_row_id=data.seat_row_id,
            name=passenger.name,
            weight_lb=passenger.weight_lb
        )

    # Post and return data
    db_session.add(new_person_on_board)
    db_session.commit()
    db_session.refresh(new_person_on_board)

    return new_person_on_board.__dict__


@router.post(
    "/baggage/{flight_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FlightBaggageReturn
)
async def add_flight_baggage(
    flight_id: int,
    data: schemas.FlightBaggageData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Add Flig Baggage Endpoint.

    Parameters: 
    - flight_id (int): flight id.
    - data (dict): baggage data

    Returns: 
    - dict: ggage data and id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exist
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile
    ).join(
        models.Aircraft,
        models.Flight.aircraft_id == models.Aircraft.id
    ).join(
        models.PerformanceProfile,
        models.Aircraft.id == models.PerformanceProfile.aircraft_id
    ).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Check baggage compartment exists
    compartment = db_session.query(models.BaggageCompartment).filter(and_(
        models.BaggageCompartment.id == data.baggage_compartment_id,
        models.BaggageCompartment.performance_profile_id == flight[2].id
    )).first()

    if compartment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baggage compartment not found."
        )

    # Post and return data
    new_baggage = models.Baggage(
        flight_id=flight_id,
        baggage_compartment_id=data.baggage_compartment_id,
        name=data.name,
        weight_lb=data.weight_lb
    )

    db_session.add(new_baggage)
    db_session.commit()
    db_session.refresh(new_baggage)

    return new_baggage.__dict__


@router.put(
    "/person-on-board/{pob_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PersonOnBoardReturn
)
async def edit_person_on_board(
    pob_id: int,
    data: schemas.PersonOnBoardData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Person On Board Endpoint.

    Parameters: 
    - pob_id (int): person on board id.
    - data (dict): name and weight of personand seat row.

    Returns: 
    - dict: person on board data and id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get person on board
    person_on_board_query = db_session.query(
        models.PersonOnBoard).filter_by(id=pob_id)

    if person_on_board_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Person not found."
        )

    # Check flight exist
    flight_id = person_on_board_query.first().flight_id
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile
    ).join(
        models.Aircraft,
        models.Flight.aircraft_id == models.Aircraft.id
    ).join(
        models.PerformanceProfile,
        models.Aircraft.id == models.PerformanceProfile.aircraft_id
    ).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Check seat-row exists
    seat_row = db_session.query(models.SeatRow).filter(and_(
        models.SeatRow.id == data.seat_row_id,
        models.SeatRow.performance_profile_id == flight[2].id
    )).first()

    if seat_row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seat row not found."
        )
    # Process data
    if data.name is not None:
        person_on_board_data = {
            "seat_row_id": data.seat_row_id,
            "name": data.name,
            "weight_lb": data.weight_lb
        }
    elif data.is_me is not None:
        user = db_session.query(models.User).filter_by(id=user_id).first()
        person_on_board_data = {
            "seat_row_id": data.seat_row_id,
            "name": user.name,
            "weight_lb": user.weight_lb
        }
    else:
        passenger = db_session.query(models.PassengerProfile).filter(and_(
            models.PassengerProfile.creator_id == user_id,
            models.PassengerProfile.id == data.passenger_profile_id
        )).first()
        if passenger is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passenger profile not found."
            )
        person_on_board_data = {
            "seat_row_id": data.seat_row_id,
            "name": passenger.name,
            "weight_lb": passenger.weight_lb
        }

    # Edit data
    person_on_board_query.update(person_on_board_data)
    db_session.commit()

    return person_on_board_query.first().__dict__


@router.put(
    "/baggage/{baggage_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FlightBaggageReturn
)
async def edit_flight_baggage(
    baggage_id: int,
    data: schemas.FlightBaggageData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Flig Baggage Endpoint.

    Parameters: 
    - baggage_id (int): flight id.
    - data (dict): baggage data

    Returns: 
    - dict: baggage data and id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get baggage
    baggage_query = db_session.query(
        models.Baggage).filter_by(id=baggage_id)

    if baggage_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baggage not found."
        )

    # Check flight exist
    flight_id = baggage_query.first().flight_id
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile
    ).join(
        models.Aircraft,
        models.Flight.aircraft_id == models.Aircraft.id
    ).join(
        models.PerformanceProfile,
        models.Aircraft.id == models.PerformanceProfile.aircraft_id
    ).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Check baggage compartment exists
    compartment = db_session.query(models.BaggageCompartment).filter(and_(
        models.BaggageCompartment.id == data.baggage_compartment_id,
        models.BaggageCompartment.performance_profile_id == flight[2].id
    )).first()

    if compartment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baggage compartment not found."
        )

    # Edit and return data
    baggage_query.update({
        "baggage_compartment_id": data.baggage_compartment_id,
        "name": data.name,
        "weight_lb": data.weight_lb
    })

    db_session.commit()

    return baggage_query.first().__dict__


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

    if not flight_query.first():
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
    deleterd_waypoints = db_session.query(models.Waypoint)\
        .filter(models.Waypoint.id.in_(waypoint_ids))\
        .delete(synchronize_session=False)
    if not deleted_flight or not deleterd_waypoints:
        raise common_responses.internal_server_error()

    db_session.commit()


@router.delete(
    "/person-on-board/{pob_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_person_on_board(
    pob_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Person On Board Endpoint.

    Parameters: 
    - pob_id (int): person on board id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get person on board
    person_on_board_query = db_session.query(
        models.PersonOnBoard).filter_by(id=pob_id)

    if person_on_board_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Person not found."
        )

    # Check flight exist
    flight_id = person_on_board_query.first().flight_id
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile
    ).join(
        models.Aircraft,
        models.Flight.aircraft_id == models.Aircraft.id
    ).join(
        models.PerformanceProfile,
        models.Aircraft.id == models.PerformanceProfile.aircraft_id
    ).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Delete data
    deleted = person_on_board_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()


@router.delete(
    "/baggage/{baggage_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_flight_baggage(
    baggage_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Person On Board Endpoint.

    Parameters: 
    - baggage_id (int): baggage id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get person on board
    baggage_query = db_session.query(
        models.Baggage).filter_by(id=baggage_id)

    if baggage_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baggage not found."
        )

    # Check flight exist
    flight_id = baggage_query.first().flight_id
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile).join(
        models.Aircraft,
        models.Flight.aircraft_id == models.Aircraft.id
    ).join(
            models.PerformanceProfile,
        models.Aircraft.id == models.PerformanceProfile.aircraft_id
    ).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Delete data
    deleted = baggage_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()
