"""
FastAPI aircraft arrangement router

This module defines the FastAPI aircraft arrangement router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import (
    check_performance_profile_and_permissions,
    get_user_id_from_email,
    check_completeness_and_make_preferred_if_complete
)

router = APIRouter(tags=["Aircraft Arrangement Data"])


@router.get(
    "/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.AircraftArrangementReturn
)
def get_aircraft_arrangement_data(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Aircraft Arrangement Data Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.

    Returns: 
    - dict: dictionary with the list of seat rows, baggage compartments and fuel tanks' data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get the performance profile and check permissions.
    check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    ).first()

    # Get bagage compartments, fuel tanks and seat rows
    baggage_compartments = db_session.query(models.BaggageCompartment).filter(
        models.BaggageCompartment.performance_profile_id == profile_id
    ).all()

    seat_rows = db_session.query(models.SeatRow).filter(
        models.SeatRow.performance_profile_id == profile_id
    ).all()

    fuel_tanks = db_session.query(models.FuelTank).filter(
        models.FuelTank.performance_profile_id == profile_id
    ).all()

    # Return data
    data = {
        "baggage_compartments": [{
            "id": compartment.id,
            "name": compartment.name,
            "arm_in": compartment.arm_in,
            "weight_limit_lb": compartment.weight_limit_lb
        } for compartment in baggage_compartments],
        "seat_rows": [{
            "id": seat.id,
            "name": seat.name,
            "arm_in": seat.arm_in,
            "weight_limit_lb": seat.weight_limit_lb,
            "number_of_seats": seat.number_of_seats
        } for seat in seat_rows],
        "fuel_tanks": [{
            "id": tank.id,
            "name": tank.name,
            "arm_in": tank.arm_in,
            "fuel_capacity_gallons": tank.fuel_capacity_gallons,
            "unusable_fuel_gallons": tank.unusable_fuel_gallons,
            "burn_sequence": tank.burn_sequence
        } for tank in fuel_tanks]
    }

    return data


@router.post(
    "/baggage-compartment/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
def post_new_baggage_compartment(
    profile_id: int,
    data: schemas.BaggageCompartmentData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Baggage Compartment Endpoint.

    Parameters: 
    - profile_id (int): profile id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check performance profile and permissions.
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )
    # Check baggage compartment name is not repeated
    baggage_compartment_exists = db_session.query(models.BaggageCompartment).filter(and_(
        models.BaggageCompartment.name == data.name,
        models.BaggageCompartment.performance_profile_id == profile_id
    )).first()
    if baggage_compartment_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment {data.name} already exists."
        )

    # Post baggage compartment
    new_baggage_compartment = models.BaggageCompartment(
        performance_profile_id=profile_id,
        name=data.name,
        arm_in=data.arm_in,
        weight_limit_lb=data.weight_limit_lb
    )

    db_session.add(new_baggage_compartment)
    db_session.commit()
    db_session.refresh(new_baggage_compartment)

    return new_baggage_compartment.__dict__


@router.post(
    "/seat-row/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.SeatRowReturn,
)
def post_new_seat_row(
    profile_id: int,
    data: schemas.SeatRowData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Seat Row Endpoint.

    Parameters: 
    - profile_id (int): profile id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check performance profile and permissions.
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )

    # Check seat row name is not repeated
    seat_row_exists = db_session.query(models.SeatRow).filter(and_(
        models.SeatRow.name == data.name,
        models.SeatRow.performance_profile_id == profile_id
    )).first()
    if seat_row_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row {data.name} for profile with id {profile_id}, already exists."
        )

    # Post seat row
    new_seat_row = models.SeatRow(
        performance_profile_id=profile_id,
        name=data.name,
        arm_in=data.arm_in,
        weight_limit_lb=data.weight_limit_lb,
        number_of_seats=data.number_of_seats
    )

    db_session.add(new_seat_row)
    db_session.commit()
    db_session.refresh(new_seat_row)
    new_seat_row_dict = {**new_seat_row.__dict__}

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )

    return new_seat_row_dict


@router.post(
    "/fuel-tank/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTankReturn,
)
def post_new_fuel_tank(
    profile_id: int,
    data: schemas.FuelTankData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Fuel Tank Endpoint.

    Parameters: 
    - profile_id (int): profile id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check performance profile and permissions.
    profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    ).first()

    profile_was_preferred = profile.is_preferred
    aircraft_id = profile.aircraft_id

    # Check fuel tank name is not repeated
    fuel_tanks = db_session.query(models.FuelTank).filter(
        models.FuelTank.performance_profile_id == profile_id
    ).all()

    if len(fuel_tanks) >= 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This profile already has 4 fuel tanks."
        )

    fuel_tank_exists = len([
        tank.name for tank in fuel_tanks
        if tank.name == data.name
    ]) > 0
    if fuel_tank_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel tank {data.name} for profile with id {profile_id}, already exists."
        )

    # Check burn sequence
    fuel_tank_higher_burn_seq = db_session.query(models.FuelTank)\
        .filter(models.FuelTank.performance_profile_id == profile_id)\
        .order_by(models.FuelTank.burn_sequence.desc()).first()

    burn_seq = min(
        [fuel_tank_higher_burn_seq.burn_sequence + 1, data.burn_sequence])

    # Post fuel tank
    new_fuel_tank = models.FuelTank(
        performance_profile_id=profile_id,
        name=data.name,
        arm_in=data.arm_in,
        fuel_capacity_gallons=data.fuel_capacity_gallons,
        unusable_fuel_gallons=data.unusable_fuel_gallons,
        burn_sequence=burn_seq
    )

    db_session.add(new_fuel_tank)
    db_session.commit()
    db_session.refresh(new_fuel_tank)
    new_fuel_tank_dict = {**new_fuel_tank.__dict__}

    # Check completeness and create fuel for existing flights
    if profile_was_preferred:
        flights = db_session.query(models.Flight).filter_by(
            aircraft_id=aircraft_id).all()

        for flight in flights:
            db_session.add(models.Fuel(
                flight_id=flight.id,
                fuel_tank_id=new_fuel_tank_dict["id"]
            ))
        db_session.commit()
    else:
        check_completeness_and_make_preferred_if_complete(
            profile_id=profile_id,
            db_session=db_session
        )

    return new_fuel_tank_dict


@router.put(
    "/baggage-compartment/{compartment_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
def edit_baggage_compartment(
    compartment_id: int,
    data: schemas.BaggageCompartmentData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Baggage Compartment Endpoint.

    Parameters: 
    - compartment_id (int): baggage compartment id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if baggage compartment doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check baggage compartment exists
    compartment_query = db_session.query(
        models.BaggageCompartment).filter_by(id=compartment_id)
    if compartment_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment with ID {compartment_id} not found."
        )

    # Check performance profile and permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=compartment_query.first().performance_profile_id
    ).first()

    # Check baggage compartment name is not repeated
    baggage_compartment_exists = db_session.query(models.BaggageCompartment).filter(and_(
        models.BaggageCompartment.name == data.name,
        models.BaggageCompartment.performance_profile_id == performance_profile.id,
        not_(models.BaggageCompartment.id == compartment_id)
    )).first()
    if baggage_compartment_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment {data.name} already exists."
        )

    # Edit baggage compartment
    compartment_query.update({
        "name": data.name,
        "arm_in": data.arm_in,
        "weight_limit_lb": data.weight_limit_lb
    })
    db_session.commit()

    return db_session.query(models.BaggageCompartment).filter_by(id=compartment_id).first().__dict__


@router.put(
    "/seat-row/{row_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.SeatRowReturn
)
def edit_seat_row(
    row_id: int,
    data: schemas.SeatRowData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Seat Row Endpoint.

    Parameters: 
    - row_id (int): seat row id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if seat row doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check seat row exists
    row_query = db_session.query(models.SeatRow).filter_by(id=row_id)
    if row_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row with ID {row_id} not found."
        )

    # Check performance profile and permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=row_query.first().performance_profile_id
    ).first()

    # Check seat row name is not repeated
    seat_row_exists = db_session.query(models.SeatRow).filter(and_(
        models.SeatRow.name == data.name,
        models.SeatRow.performance_profile_id == performance_profile.id,
        not_(models.SeatRow.id == row_id)
    )).first()
    if seat_row_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row {data.name} already exists."
        )

    # Edit seat row
    row_query.update({
        "name": data.name,
        "arm_in": data.arm_in,
        "weight_limit_lb": data.weight_limit_lb,
        "number_of_seats": data.number_of_seats
    })
    db_session.commit()

    return db_session.query(models.SeatRow).filter_by(id=row_id).first().__dict__


@router.put(
    "/fuel-tank/{tank_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTankReturn
)
def edit_fuel_tank(
    tank_id: int,
    data: schemas.FuelTankData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit fuel tank Endpoint.

    Parameters: 
    - tank_id (int): fuel tank id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if fuel tank doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check fuel tank exists
    tank_query = db_session.query(models.FuelTank).filter_by(id=tank_id)
    if tank_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel tank with ID {tank_id} not found."
        )

    # Check performance profile and permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=tank_query.first().performance_profile_id
    ).first()

    # Check fuel tank name is not repeated
    fuel_tank_exists = db_session.query(models.FuelTank).filter(and_(
        models.FuelTank.name == data.name,
        models.FuelTank.performance_profile_id == performance_profile.id,
        not_(models.FuelTank.id == tank_id)
    )).first()
    if fuel_tank_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel tank {data.name} already exists."
        )

    # Check burn sequence
    fuel_tank_higher_burn_seq = db_session.query(models.FuelTank)\
        .filter(and_(
            models.FuelTank.performance_profile_id == performance_profile.id,
            not_(models.FuelTank.id == tank_id)
        )).order_by(models.FuelTank.burn_sequence.desc()).first()

    burn_seq = min(
        [fuel_tank_higher_burn_seq.burn_sequence + 1, data.burn_sequence])

    # Edit fuel tank
    tank_query.update({
        "name": data.name,
        "arm_in": data.arm_in,
        "fuel_capacity_gallons": data.fuel_capacity_gallons,
        "unusable_fuel_gallons": data.unusable_fuel_gallons,
        "burn_sequence": burn_seq
    })
    db_session.commit()

    return db_session.query(models.FuelTank).filter_by(id=tank_id).first().__dict__


@router.delete(
    "/baggage-compartment/{compartment_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_baggage_compartment(
    compartment_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Baggage Compartment Endpoint.

    Parameters: 
    - compartment_id (int): baggage compartment id.

    Returns: None

    Raise:
    - HTTPException (400): if baggage compartment id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check baggage compartment exists
    compartment_query = db_session.query(
        models.BaggageCompartment).filter_by(id=compartment_id)
    if compartment_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment with ID {compartment_id} not found."
        )

    # Check performance profile and permissions.
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=compartment_query.first().performance_profile_id
    ).first()

    # Delete baggage compartment
    deleted = compartment_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()


@router.delete("/seat-row/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_seat_row(
    row_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Seat Row Endpoint.

    Parameters: 
    - row_id (int): seat row id.

    Returns: None

    Raise:
    - HTTPException (400): if seat row id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check seat row exists
    row_query = db_session.query(models.SeatRow).filter_by(id=row_id)
    if row_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row with ID {row_id} not found."
        )

    # Check performance profile and permissions.
    performance_profile_id = row_query.first().performance_profile_id
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=performance_profile_id
    ).first()

    # Delete seat row
    deleted = row_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=performance_profile_id,
        db_session=db_session
    )


@router.delete("/fuel-tank/{tank_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fuel_tank(
    tank_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Fuel Tank Endpoint.

    Parameters: 
    - tank_id (int): fuel tank id.

    Returns: None

    Raise:
    - HTTPException (400): if fuel tank id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check fuel tank exists
    tank_query = db_session.query(models.FuelTank).filter_by(id=tank_id)
    if tank_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel tank with ID {tank_id} not found."
        )

    # Check performance profile and permissions.
    performance_profile_id = tank_query.first().performance_profile_id
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=performance_profile_id
    ).first()

    # Delete seat row
    deleted = tank_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=performance_profile_id,
        db_session=db_session
    )
