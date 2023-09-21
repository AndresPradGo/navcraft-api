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
from functions.data_processing import (
    check_performance_profile_and_permissions,
    get_user_id_from_email,
    check_completeness_and_make_preferred_if_complete
)

router = APIRouter(tags=["Aircraft Weight and Balance Data"])


@router.get(
    "/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GetWeightBalanceData
)
async def get_weight_balance_data(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Weight and Balance Data Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.

    Returns: 
    - dict: dictionary with the weight and balance data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get the performance profile and check permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
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

    # Get weight and balance profiles
    weight_balance_profiles = db_session.query(models.WeightBalanceProfile).filter(
        models.WeightBalanceProfile.performance_profile_id == profile_id
    ).all()

    wb_profile_ids = [wb.id for wb in weight_balance_profiles]
    weight_balance_profile_limits = db_session.query(models.WeightBalanceLimit).filter(
        models.WeightBalanceLimit.weight_balance_profile_id.in_(wb_profile_ids)
    ).all()

    # Return weight and balance data
    data = {
        "center_of_gravity_in": performance_profile.center_of_gravity_in
        if performance_profile.center_of_gravity_in is not None else 0,
        "empty_weight_lb": performance_profile.empty_weight_lb
        if performance_profile.empty_weight_lb is not None else 0,
        "max_ramp_weight_lb": performance_profile.max_ramp_weight_lb
        if performance_profile.max_ramp_weight_lb is not None else 0,
        "max_landing_weight_lb": performance_profile.max_landing_weight_lb
        if performance_profile.max_landing_weight_lb is not None else 0,
        "baggage_allowance_lb": performance_profile.baggage_allowance_lb
        if performance_profile.baggage_allowance_lb is not None else 0,
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
        } for tank in fuel_tanks],
        "weight_balance_profiles": [{
            "id": profile.id,
            "name": profile.name,
            "max_take_off_weight_lb": profile.max_take_off_weight_lb,
            "limits": [{
                "id": limit.id,
                "from_cg_in": limit.from_cg_in,
                "from_weight_lb": limit.from_weight_lb,
                "to_cg_in": limit.to_cg_in,
                "to_weight_lb": limit.to_weight_lb
            } for limit in weight_balance_profile_limits]
        } for profile in weight_balance_profiles]
    }

    return data


@router.post(
    "/baggage-compartment/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
async def post_new_baggage_compartment(
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
        user_id=await get_user_id_from_email(
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
async def post_new_seat_row(
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
        user_id=await get_user_id_from_email(
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
async def post_new_fuel_tank(
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
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )

    # Check fuel tank name is not repeated
    fuel_tank_exists = db_session.query(models.FuelTank).filter(and_(
        models.FuelTank.name == data.name,
        models.FuelTank.performance_profile_id == profile_id
    )).first()
    if fuel_tank_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel tank {data.name} for profile with id {profile_id}, already exists."
        )

    # Post fuel tank
    new_fuel_tank = models.FuelTank(
        performance_profile_id=profile_id,
        name=data.name,
        arm_in=data.arm_in,
        fuel_capacity_gallons=data.fuel_capacity_gallons,
        unusable_fuel_gallons=data.unusable_fuel_gallons,
        burn_sequence=data.burn_sequence
    )

    db_session.add(new_fuel_tank)
    db_session.commit()
    db_session.refresh(new_fuel_tank)
    new_fuel_tank_dict = {**new_fuel_tank.__dict__}

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )

    return new_fuel_tank_dict


@router.post(
    "/weight-balance-profile/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
async def post_new_weight_and_balance_profile(
    profile_id: int,
    data: schemas.WeightBalanceData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
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

    # Check performance profile and permissions.
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )

    # Check maximum number of W&B profiles is 4
    wb_profiles = db_session.query(models.WeightBalanceProfile).filter(
        models.WeightBalanceProfile.performance_profile_id == profile_id
    ).all()

    if len(wb_profiles) >= 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of W&B profiles per performance profile is 4."
        )

    # Check weight and balance profile doesn't already exist
    wb_profile_exists = db_session.query(
        models.WeightBalanceProfile).filter(and_(
            models.WeightBalanceProfile.name == data.name,
            models.WeightBalanceProfile.performance_profile_id == profile_id
        )).first()
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

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )

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
    "/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
async def edit_weight_and_balance_data_for_performance_profile(
    profile_id: int,
    performance_data: schemas.PerformanceProfileWeightBalanceData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Weight And Balance Data For Performance Profile Endpoint.

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

    # Check performance profile and permissions.
    performance_profile_query = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )

    # Update profile
    performance_profile_query.update({
        "center_of_gravity_in": performance_data.center_of_gravity_in,
        "empty_weight_lb": performance_data.empty_weight_lb,
        "max_ramp_weight_lb": performance_data.max_ramp_weight_lb,
        "max_landing_weight_lb": performance_data.max_landing_weight_lb,
        "baggage_allowance_lb": performance_data.baggage_allowance_lb
    })
    db_session.commit()

    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )

    # Return profile
    new_performance_profile = db_session.query(
        models.PerformanceProfile).filter_by(id=profile_id).first()

    fuel_tanks = db_session.query(models.FuelTank).filter_by(
        performance_profile_id=profile_id).all()

    fuel_capacity = sum([tank.fuel_capacity_gallons for tank in fuel_tanks])
    unusable_fuel = sum([tank.unusable_fuel_gallons for tank in fuel_tanks])

    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name,
        "fuel_capacity_gallons": fuel_capacity,
        "unusable_fuel_gallons": unusable_fuel
    }


@router.put(
    "/baggage-compartment/{compartment_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
async def edit_baggage_compartment(
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
        user_id=await get_user_id_from_email(
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
async def edit_seat_row(
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
        user_id=await get_user_id_from_email(
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
async def edit_fuel_tank(
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
        user_id=await get_user_id_from_email(
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

    # Edit fuel tank
    tank_query.update({
        "name": data.name,
        "arm_in": data.arm_in,
        "fuel_capacity_gallons": data.fuel_capacity_gallons,
        "unusable_fuel_gallons": data.number_of_seats,
        "burn_sequence": data.burn_sequence
    })
    db_session.commit()

    return db_session.query(models.SeatRow).filter_by(id=tank_id).first().__dict__


@router.put(
    "/weight-balance-profile/{wb_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
async def edit_weight_and_balance_profile(
    wb_profile_id: int,
    data: schemas.WeightBalanceData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
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

    # Check performance profile and permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=wb_profile_query.first().performance_profile_id
    ).first()

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
        models.WeightBalanceLimit.weight_balance_profile_id == wb_profile_id
    ).delete(synchronize_session="evaluate")

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
        user_id=await get_user_id_from_email(
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
async def delete_seat_row(
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
        user_id=await get_user_id_from_email(
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
async def delete_fuel_tank(
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
        user_id=await get_user_id_from_email(
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


@router.delete("/weight-balance-profile/{wb_profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight_and_balance_profile(
    wb_profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
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

    # Check if performance profile and permissions
    performance_profile_id = wb_profile_query.first().performance_profile_id
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=performance_profile_id
    ).first()

    # Delete W&B Profile
    deleted = wb_profile_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=performance_profile_id,
        db_session=db_session
    )
