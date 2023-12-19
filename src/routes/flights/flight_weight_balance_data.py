"""
FastAPI flight weight and balance data router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import get_user_id_from_email

router = APIRouter(tags=["Flight Weight and Balance Data"])


@router.get(
    "/person-on-board/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.PersonOnBoardReturn]
)
def get_all_persons_on_board(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Persons On Board Of Flight Endpoint.

    Parameters:
    - Flight_id (int): flight id.

    Returns: 
    - list: list of person on board dictionaries.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exist
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Get POBs
    persons_on_board = db_session.query(models.PersonOnBoard).filter(
        models.PersonOnBoard.flight_id == flight_id
    ).all()

    pob_list = []
    for person_on_board in persons_on_board:
        if person_on_board.user_id is not None:
            user = db_session.query(models.User).filter_by(
                id=person_on_board.user_id).first()
            pob_list.append({
                "id": person_on_board.id,
                "seat_number": person_on_board.seat_number,
                "seat_row_id": person_on_board.seat_row_id,
                "name": user.name,
                "weight_lb": user.weight_lb,
                "user_id": person_on_board.user_id,
            })
        elif person_on_board.passenger_profile_id is not None:
            passenger = db_session.query(models.PassengerProfile).filter(and_(
                models.PassengerProfile.creator_id == user_id,
                models.PassengerProfile.id == person_on_board.passenger_profile_id
            )).first()
            user = db_session.query(models.User).filter_by(
                id=person_on_board.user_id).first()
            pob_list.append({
                "id": person_on_board.id,
                "seat_number": person_on_board.seat_number,
                "seat_row_id": person_on_board.seat_row_id,
                "name": passenger.name,
                "weight_lb": passenger.weight_lb,
                "passenger_profile_id": passenger.id,
            })
        else:
            pob_list.append({
                "id": person_on_board.id,
                "seat_number": person_on_board.seat_number,
                "seat_row_id": person_on_board.seat_row_id,
                "name": person_on_board.name,
                "weight_lb": person_on_board.weight_lb,
            })

    return pob_list


@router.get(
    "/baggage/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.FlightBaggageReturn]
)
def get_all_flight_baggage(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Flight Baggage Endpoint.

    Parameters:
    - Flight_id (int): flight id.

    Returns: 
    - list: list of baggage dictionaries.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exist
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Get baggage
    baggages = db_session.query(models.Baggage).filter(
        models.Baggage.flight_id == flight_id
    ).all()

    baggage_list = []
    for baggage in baggages:
        baggage_list.append({
            "id": baggage.id,
            "baggage_compartment_id": baggage.baggage_compartment_id,
            "name": baggage.name,
            "weight_lb": baggage.weight_lb,
        })

    return baggage_list


@router.get(
    "/fuel/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.FlightFuelReturn]
)
def get_all_flight_fuel(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Flight Fuel Endpoint.

    Parameters:
    - Flight_id (int): flight id.

    Returns: 
    - list: list of dictionaries with fuel tank.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exist
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Get fuel density
    fuel_type = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile,
        models.FuelType
    )\
        .join(models.Aircraft, models.Flight.aircraft_id == models.Aircraft.id)\
        .join(models.PerformanceProfile, models.Aircraft.id == models.PerformanceProfile.aircraft_id)\
        .join(models.FuelType, models.PerformanceProfile.fuel_type_id == models.FuelType.id)\
        .filter(and_(
            models.Flight.id == flight_id,
            models.PerformanceProfile.is_preferred.is_(True)
        )).first()

    # Get fuel
    fuel_tanks = db_session.query(models.Fuel).filter(
        models.Fuel.flight_id == flight_id
    ).all()

    if len(fuel_tanks) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fuel tanks found. This may be because aircraft doesn't have a preferred profile."
        )

    fuel_list = []
    for fuel in fuel_tanks:
        fuel_list.append({
            "id": fuel.id,
            "fuel_tank_id": fuel.fuel_tank_id,
            "gallons": fuel.gallons,
            "weight_lb": fuel_type[3].density_lb_gal * fuel.gallons
        })

    return fuel_list


@router.post(
    "/person-on-board/{flight_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PersonOnBoardReturn
)
def add_person_on_board(
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
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exist
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
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

    if seat_row.number_of_seats < data.seat_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seat not found."
        )

    # Process data
    if data.name is not None:
        pob_exists = db_session.query(models.PersonOnBoard).filter(and_(
            models.PersonOnBoard.flight_id == flight_id,
            models.PersonOnBoard.name == data.name,
        )).first() is not None

        if pob_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{data.name} is already on this flight."
            )

        new_person_on_board = models.PersonOnBoard(
            flight_id=flight_id,
            seat_number=data.seat_number,
            seat_row_id=data.seat_row_id,
            name=data.name,
            weight_lb=data.weight_lb
        )
    elif data.is_me is not None:
        user = db_session.query(models.User).filter_by(id=user_id).first()
        pob_exists = db_session.query(models.PersonOnBoard).filter(and_(
            models.PersonOnBoard.flight_id == flight_id,
            or_(
                models.PersonOnBoard.user_id == user_id,
                models.PersonOnBoard.name == user.name
            ),
        )).first() is not None
        if pob_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user.name} is already on this flight."
            )

        new_person_on_board = models.PersonOnBoard(
            flight_id=flight_id,
            seat_number=data.seat_number,
            seat_row_id=data.seat_row_id,
            user_id=user_id
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

        pob_exists = db_session.query(models.PersonOnBoard).filter(and_(
            models.PersonOnBoard.flight_id == flight_id,
            or_(
                models.PersonOnBoard.passenger_profile_id == passenger.id,
                models.PersonOnBoard.name == passenger.name
            ),
        )).first() is not None
        if pob_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{passenger.name} is already on this flight."
            )

        new_person_on_board = models.PersonOnBoard(
            flight_id=flight_id,
            seat_number=data.seat_number,
            seat_row_id=data.seat_row_id,
            passenger_profile_id=passenger.id
        )

    # Post and return data
    db_session.add(new_person_on_board)
    db_session.commit()
    db_session.refresh(new_person_on_board)
    new_person_on_board_dict = {**new_person_on_board.__dict__}

    if new_person_on_board_dict["user_id"] is not None:
        user = db_session.query(models.User).filter_by(id=user_id).first()
        return {
            "id": new_person_on_board_dict["id"],
            "seat_row_id": new_person_on_board_dict["seat_row_id"],
            "seat_number": new_person_on_board_dict["seat_number"],
            "name": user.name,
            "weight_lb": user.weight_lb,
            "user_id": new_person_on_board_dict["user_id"],
        }

    if new_person_on_board_dict["passenger_profile_id"] is not None:
        passenger = db_session.query(models.PassengerProfile).filter(and_(
            models.PassengerProfile.creator_id == user_id,
            models.PassengerProfile.id == data.passenger_profile_id
        )).first()
        return {
            "id": new_person_on_board_dict["id"],
            "seat_row_id": new_person_on_board_dict["seat_row_id"],
            "seat_number": new_person_on_board_dict["seat_number"],
            "name": passenger.name,
            "weight_lb": passenger.weight_lb,
            "passenger_profile_id": new_person_on_board_dict["passenger_profile_id"],
        }

    return new_person_on_board_dict


@router.post(
    "/baggage/{flight_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FlightBaggageReturn
)
def add_flight_baggage(
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
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
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

    # Check baggage doesn't already exist
    baggage_exists = db_session.query(models.Baggage).filter(and_(
        models.Baggage.flight_id == flight_id,
        models.Baggage.name == data.name,
    )).first()

    if baggage_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{data.name} already loaded to this flight."
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
    status_code=status.HTTP_200_OK,
    response_model=schemas.PersonOnBoardReturn
)
def edit_person_on_board(
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
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
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

    if seat_row.number_of_seats < data.seat_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seat not found."
        )
    # Process data
    if data.name is not None:
        pob_exists = db_session.query(models.PersonOnBoard).filter(and_(
            models.PersonOnBoard.flight_id == flight_id,
            models.PersonOnBoard.name == data.name,
            not_(models.PersonOnBoard.id == pob_id)
        )).first() is not None

        if pob_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{data.name} is already on this flight."
            )
        person_on_board_data = {
            "seat_row_id": data.seat_row_id,
            "seat_number": data.seat_number,
            "name": data.name,
            "weight_lb": data.weight_lb,
            "user_id": None,
            "passenger_profile_id": None
        }

    elif data.is_me is not None:
        user = db_session.query(models.User).filter_by(id=user_id).first()
        pob_exists = db_session.query(models.PersonOnBoard).filter(and_(
            models.PersonOnBoard.flight_id == flight_id,
            or_(
                models.PersonOnBoard.user_id == user_id,
                models.PersonOnBoard.name == user.name
            ),
            not_(models.PersonOnBoard.id == pob_id)
        )).first() is not None
        if pob_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user.name} is already on this flight."
            )
        person_on_board_data = {
            "seat_row_id": data.seat_row_id,
            "seat_number": data.seat_number,
            "user_id": user_id,
            "name": None,
            "weight_lb": None
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
        pob_exists = db_session.query(models.PersonOnBoard).filter(and_(
            models.PersonOnBoard.flight_id == flight_id,
            or_(
                models.PersonOnBoard.passenger_profile_id == user_id,
                models.PersonOnBoard.name == passenger.name
            ),
            not_(models.PersonOnBoard.id == pob_id)
        )).first() is not None

        if pob_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user.name} is already on this flight."
            )
        person_on_board_data = {
            "seat_row_id": data.seat_row_id,
            "seat_number": data.seat_number,
            "passenger_profile_id": passenger.id,
            "name": None,
            "weight_lb": None
        }

    # Edit data
    person_on_board_query.update(person_on_board_data)
    db_session.commit()

    # Return data
    new_person_on_board_dict = {**person_on_board_query.first().__dict__}
    if new_person_on_board_dict["user_id"] is not None:
        user = db_session.query(models.User).filter_by(id=user_id).first()
        return {
            "id": new_person_on_board_dict["id"],
            "seat_row_id": new_person_on_board_dict["seat_row_id"],
            "seat_number": new_person_on_board_dict["seat_number"],
            "name": user.name,
            "weight_lb": user.weight_lb,
            "user_id": new_person_on_board_dict["user_id"],
        }

    if new_person_on_board_dict["passenger_profile_id"] is not None:
        passenger = db_session.query(models.PassengerProfile).filter(and_(
            models.PassengerProfile.creator_id == user_id,
            models.PassengerProfile.id == data.passenger_profile_id
        )).first()
        return {
            "id": new_person_on_board_dict["id"],
            "seat_row_id": new_person_on_board_dict["seat_row_id"],
            "seat_number": new_person_on_board_dict["seat_number"],
            "name": passenger.name,
            "weight_lb": passenger.weight_lb,
            "passenger_profile_id": new_person_on_board_dict["passenger_profile_id"],
        }

    return new_person_on_board_dict


@router.put(
    "/baggage/{baggage_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.FlightBaggageReturn
)
def edit_flight_baggage(
    baggage_id: int,
    data: schemas.FlightBaggageData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Flight Baggage Endpoint.

    Parameters: 
    - baggage_id (int): baggage id.
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
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
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

    # Check baggage doesn't already exist
    baggage_exists = db_session.query(models.Baggage).filter(and_(
        models.Baggage.flight_id == flight_id,
        models.Baggage.name == data.name,
        not_(models.Baggage.id == baggage_id)
    )).first()

    if baggage_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{data.name} is already loaded on this flight."
        )

    # Edit and return data
    baggage_query.update({
        "baggage_compartment_id": data.baggage_compartment_id,
        "name": data.name,
        "weight_lb": data.weight_lb
    })

    db_session.commit()

    return baggage_query.first().__dict__


@router.put(
    "/fuel/{fuel_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.FlightFuelReturn
)
def edit_flight_fuel(
    fuel_id: int,
    data: schemas.FuelData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Flight Fuel Endpoint.

    Parameters: 
    - fuel_id (int): fuel id.
    - data (dict): dict with gallons of fuel in tank

    Returns: 
    - dict: fuel data and id.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get fuel
    fuel_query = db_session.query(
        models.Fuel).filter_by(id=fuel_id)

    if fuel_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fuel not found."
        )

    # Check flight exist
    flight_id = fuel_query.first().flight_id
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(
        models.Flight,
        models.Aircraft,
        models.PerformanceProfile,
        models.FuelType
    ).join(
        models.Aircraft,
        models.Flight.aircraft_id == models.Aircraft.id
    ).join(
        models.PerformanceProfile,
        models.Aircraft.id == models.PerformanceProfile.aircraft_id
    ).join(
        models.FuelType,
        models.PerformanceProfile.fuel_type_id == models.FuelType.id
    ).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()

    fuel_density = flight[3].density_lb_gal

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

   # Check fuel quantity is less than or equal to tank's capacity
    fuel_tank_id = fuel_query.first().fuel_tank_id
    fuel_tank = db_session.query(
        models.FuelTank).filter_by(id=fuel_tank_id).first()
    total_capacity = fuel_tank.fuel_capacity_gallons
    if total_capacity < data.gallons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Total capacity of {fuel_tank.name} is {total_capacity} gallons."
        )
    # Edit and return data
    fuel_query.update({"gallons": data.gallons})

    db_session.commit()

    fuel = fuel_query.first().__dict__

    return {
        "id": fuel["id"],
        "fuel_tank_id": fuel["fuel_tank_id"],
        "gallons": fuel["gallons"],
        "weight_lb": fuel_density * fuel["gallons"]
    }


@router.delete(
    "/person-on-board/{pob_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_person_on_board(
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
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
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
def delete_flight_baggage(
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
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
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
