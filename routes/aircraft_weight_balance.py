"""
FastAPI aircraft weight and balance router

This module defines the FastAPI aircraft weight and balance router endpoints.

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

router = APIRouter(tags=["Aircraft Weight and Balance"])


@router.post(
    "/model/baggage-compartment/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
async def post_new_baggage_compartment(
    profile_id: int,
    data: schemas.BaggageCompartmentData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
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

    # Check if performance profile exists
    performance_profile = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} doesn't exist."
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
    "/model/seat-row/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.SeatRowReturn,
)
async def post_new_seat_row(
    profile_id: int,
    data: schemas.SeatRowData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
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

    # Check if performance profile exists
    performance_profile = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} doesn't exist."
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

    # Post baggage compartment
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

    return new_seat_row.__dict__


@router.post(
    "/model/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
async def post_new_weight_and_balance_profile(
    profile_id: int,
    data: schemas.WeightBalanceData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Weight And Balance Profile Endpoint.

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

    # Check performance profile exists
    performance_profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id,
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.model_id.isnot(None)
    )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model performance profile with ID {profile_id} was not found."
        )

    # Check weight and balance profile doesn't already exist
    wb_profile_exists = db_session.query(
        models.WeightBalanceProfile).filter_by(name=data.name).first()
    if wb_profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weight and Balance profile {data.name} already exists."
        )

    # Post weight and balance profile
    new_profile = models.WeightBalanceProfile(
        performance_profile_id=profile_id,
        name=data.name,
        max_take_off_weight_lb=data.max_take_off_weight_lb
    )
    db_session.add(new_profile)
    db_session.commit()
    db_session.refresh(new_profile)

    # Post weight and balance limits
    wb_profile_id = new_profile.id
    new_limits = [models.WeightBalanceLimit(
        weight_balance_profile_id=wb_profile_id,
        from_cg_in=limit.from_cg_in,
        from_weight_lb=limit.from_weight_lb,
        to_cg_in=limit.to_cg_in,
        to_weight_lb=limit.to_weight_lb,
    ) for limit in data.limits]

    db_session.add_all(new_limits)
    db_session.commit()

    # Return weight and balance profile
    weight_balance_profile = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id).first()
    limits = db_session.query(models.WeightBalanceLimit).filter_by(
        weight_balance_profile_id=wb_profile_id).all()

    return {
        **weight_balance_profile.__dict__,
        "limits": [limit.__dict__ for limit in limits]
    }


@router.put(
    "/model/performance/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfilePostReturn
)
async def edit_weight_and_balance_data_for_aircraft_model_performance_profile(
    profile_id: int,
    performance_data: schemas.PerformanceProfileWightBalanceData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit  Weight And Balance Data For Model Performance Profile Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the performance profile data, and the id.

    Raise:
    - HTTPException (400): if performance profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check profile exists
    performance_profile_query = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        ))
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} doesn't exist."
        )
    # Update profile
    performance_profile_query.update({
        "center_of_gravity_in": performance_data.center_of_gravity_in,
        "empty_weight_lb": performance_data.empty_weight_lb,
        "max_ramp_weight_lb": performance_data.max_ramp_weight_lb,
        "max_landing_weight_lb": performance_data.max_landing_weight_lb,
        "fuel_arm_in": performance_data.fuel_arm_in,
        "fuel_capacity_gallons": performance_data.fuel_capacity_gallons
    })
    db_session.commit()

    new_performance_profile = db_session.query(
        models.PerformanceProfile).filter_by(id=profile_id).first()
    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name
    }


@router.put(
    "/performance/baggage-compartment/{compartment_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
async def edit_baggage_compartment(
    compartment_id: int,
    data: schemas.BaggageCompartmentData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
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

    # Check performance profile
    performance_profile = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == compartment_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Performance profile you're trying to edit, is not for an aircraft model."
        )

    # Check baggage compartment name is not repeated
    baggage_compartment_exists = db_session.query(models.BaggageCompartment).filter(and_(
        models.BaggageCompartment.name == data.name,
        models.BaggageCompartment.performance_profile_id == performance_profile.id,
        not_(models.BaggageCompartment.id == compartment_id)
    )).first()
    error_msg = f"Baggage compartment {data.name} already exists."
    if baggage_compartment_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
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
    "/performance/seat-row/{row_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.SeatRowReturn
)
async def edit_seat_row(
    row_id: int,
    data: schemas.SeatRowData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
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

    # Check baggage compartment exists
    row_query = db_session.query(models.SeatRow).filter_by(id=row_id)
    if row_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row with ID {row_id} not found."
        )

    # Check performance profile
    performance_profile = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == row_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Performance profile you're trying to edit, is not for an aircraft model."
        )

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
    "/model/{wb_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
async def edit_weight_and_balance_profile(
    wb_profile_id: int,
    data: schemas.WeightBalanceData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Weight And Balance Profile Endpoint.

    Parameters: 
    - wb_profile_id (int): weight and balance id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if weight and balance doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if W&B ID exists
    wb_profile_query = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id)
    if wb_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"W&B Profile with ID {wb_profile_id} was not found."
        )

    # Check if performance profile is for model
    performance_profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == wb_profile_query.first().performance_profile_id,
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.model_id.isnot(None)
    )).first()

    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The performance profile you are trying to edit is not for and aircraft model."
        )

    # Check weight and balance profile doesn't already exist
    wb_profile_exists = db_session.query(
        models.WeightBalanceProfile).filter(and_(
            models.WeightBalanceProfile.name == data.name,
            models.WeightBalanceProfile.performance_profile_id == performance_profile.id,
            not_(models.WeightBalanceProfile.id == wb_profile_id)
        )).first()
    if wb_profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weight and Balance profile '{data.name}' already exists."
        )

    # Update weight and balance limts
    new_limits = [models.WeightBalanceLimit(
        weight_balance_profile_id=wb_profile_id,
        from_cg_in=limit.from_cg_in,
        from_weight_lb=limit.from_weight_lb,
        to_cg_in=limit.to_cg_in,
        to_weight_lb=limit.to_weight_lb
    ) for limit in data.limits]

    _ = db_session.query(models.WeightBalanceLimit).filter(
        models.WeightBalanceLimit.weight_balance_profile_id == wb_profile_id).delete()

    db_session.add_all(new_limits)

    # Update weight and balance profile
    wb_profile_query.update({
        "name": data.name,
        "max_take_off_weight_lb": data.max_take_off_weight_lb
    })

    db_session.commit()

    # Return weight and balance profile
    weight_balance_profile = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id).first()
    limits = db_session.query(models.WeightBalanceLimit).filter_by(
        weight_balance_profile_id=wb_profile_id).all()

    return {
        **weight_balance_profile.__dict__,
        "limits": [limit.__dict__ for limit in limits]
    }


@router.delete(
    "/baggage-compartment/{compartment_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_baggage_compartment(
    compartment_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
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

    # Check parformance profile is for an aircraft model
    performance_profile = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == compartment_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Performance profile you're trying to edit, is not for an aircraft model."
        )

    # Delete baggage compartment
    deleted = compartment_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()


@router.delete("/seat-row/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seat_row(
    row_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
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

    # Check performance profile is for an aircraft model
    performance_profile = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == row_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Performance profile you're trying to edit, is not for an aircraft model."
        )

    # Delete seat row
    deleted = row_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()


@router.delete("/model/{wb_profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight_and_balance_profile(
    wb_profile_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Weight and Balance Profile Endpoint.

    Parameters: 
    - wb_profile_id (int): weight and balance id.

    Returns: None

    Raise:
    - HTTPException (400): if W&B profile id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if W&B ID exists
    wb_profile_query = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id)
    if wb_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"W&B Profile with ID {wb_profile_id} was not found."
        )

    # Check if performance profile is for model
    is_aircraft_model_profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == wb_profile_query.first().performance_profile_id,
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.model_id.isnot(None)
    )).first()

    if is_aircraft_model_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The performance profile you are trying to edit is not for and aircraft model."
        )

    # Delete W&B Profile
    deleted = wb_profile_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()
