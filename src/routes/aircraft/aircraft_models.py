"""
FastAPI aircraft models router

This module defines the FastAPI aircraft models endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import ValidationError
import pytz
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db

router = APIRouter(tags=["Aircraft Model"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.GetPerformanceProfileList]
)
def get_performance_profile_model_list(
    profile_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Performance Profile Model List Endpoint.

    Parameters: 
    - profile_id (int [optional]): If provided, only 1 profile will be provided.

    Returns: 
    - List[dict[GetPerformanceProfileList]]: list of dictionaries with profile data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get performance profile models
    user_is_active_admin = current_user.is_active and current_user.is_admin
    performance_profiles = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.aircraft_id.is_(None),
        or_(
            not_(profile_id),
            models.PerformanceProfile.id == profile_id
        ),
        or_(
            models.PerformanceProfile.is_complete,
            user_is_active_admin
        )
    )).all()

    # Organize performance profile list
    try:
        profiles = [schemas.GetPerformanceProfileList(
            id=profile.id,
            performance_profile_name=profile.name,
            is_complete=profile.is_complete,
            fuel_type_id=profile.fuel_type_id,
            created_at_utc=pytz.timezone('UTC').localize((profile.created_at)),
            last_updated_utc=pytz.timezone(
                'UTC').localize((profile.last_updated))
        ) for profile in performance_profiles]
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    return profiles


@router.get(
    "/fuel-type",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.FuelTypeReturn]
)
def get_fuel_types(
    fuel_type_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Fuel Types Endpoint.

    Parameters: 
    - fuel_type_id (int): fuel type id, for returning only 1 fuel type. If 0 or none, 
      it returns all entries. If id doesn't exist, it returns an empty list

    Returns: 
    - list[dict[FuelTypeReturn]]: list of dictionaries with the fuel types.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    return db_session.query(models.FuelType).filter(or_(
        not_(fuel_type_id),
        models.FuelType.id == fuel_type_id
    )).order_by(models.FuelType.name).all()


@router.post(
    "/fuel-type",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTypeReturn
)
def post_new_fuel_type(
    fuel_type: schemas.FuelTypeData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Fuel Type Endpoint.

    Parameters: 
    - fuel_type (dict[FuelTypeData]): the fuel type data to be added.

    Returns: 
    - dic[FuelTypeReturn]: dictionary with the fuel type data added to the database, and the id.

    Raise:
    - HTTPException (400): if fuel type already exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if fuel type already exists in database
    fuelt_type_exists = db_session.query(models.FuelType).filter_by(
        name=fuel_type.name).first()
    if fuelt_type_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{fuel_type.name} fuel already exists in the database."
        )
    # Add fuel type to database
    new_fuel_type = models.FuelType(**fuel_type.model_dump())
    db_session.add(new_fuel_type)
    db_session.commit()

    # Return fuel type data
    db_session.refresh(new_fuel_type)

    return new_fuel_type


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
def post_new_performance_profile(
    performance_data: schemas.OfficialPerformanceProfileData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Performance Profile Endpoint.

    Parameters: 
    - performance_data (dict[OfficialPerformanceProfileData]): dictionary with 
      the performance data to be added.

    Returns: 
    - dic[PerformanceProfileReturn]: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check profile is not repeated
    profile_exists = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.name == performance_data.performance_profile_name
    )).first()

    if profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{performance_data.performance_profile_name}' Profile already exists."
        )

    # Check fuel type exists
    fuel_type_id_exists = db_session.query(models.FuelType).filter_by(
        id=performance_data.fuel_type_id).first()
    if not fuel_type_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type ID {performance_data.fuel_type_id} doesn't exist."
        )

    # Post profile
    new_performance_profile = models.PerformanceProfile(
        fuel_type_id=performance_data.fuel_type_id,
        name=performance_data.performance_profile_name,
        is_complete=performance_data.is_complete
    )
    db_session.add(new_performance_profile)
    db_session.commit()

    # Return profile
    db_session.refresh(new_performance_profile)
    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name,
        "created_at_utc": pytz.timezone('UTC').localize((new_performance_profile.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_performance_profile.last_updated))
    }


@router.put(
    "/fuel-type/{fuel_type_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTypeReturn
)
def edit_fuel_type(
    fuel_type_id: int,
    fuel_type: schemas.FuelTypeData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Fuel Type Endpoint.

    Parameters: 
    - fuel_type_id (int): fuel type id.
    - fuel_type (dict[FuelTypeData]): the fuel type data to be added.

    Returns: 
    - dic[FuelTypeReturn]: dictionary with the new fuel type data.

    Raise:
    - HTTPException (400): if fuel type doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check id is valid
    fuelt_type_query = db_session.query(models.FuelType).filter(
        models.FuelType.id == fuel_type_id)

    if not fuelt_type_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type with id {fuel_type_id} doesn't exists in the database."
        )

    # Check if fuel type with same name exists
    fuelt_type_exists = db_session.query(models.FuelType).filter(and_(
        models.FuelType.name == fuel_type.name,
        not_(models.FuelType.id == fuel_type_id)
    )).first()
    if fuelt_type_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{fuel_type.name} fuel already exists in the database."
        )
    # Edit fuel type
    fuelt_type_query.update(fuel_type.model_dump())
    db_session.commit()

    # Return fuel type data
    return fuelt_type_query.first().__dict__


@router.put(
    "/{performance_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
def edit_performance_profile(
    performance_profile_id: int,
    performance_data: schemas.OfficialPerformanceProfileData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Performance Profile Endpoint.

    Parameters: 
    - performance_profile_id (int): performance profile id.
    - performance_data (dict[OfficialPerformanceProfileData]): the 
      performance data to be added.

    Returns: 
    - dic[PerformanceProfileReturn]: dictionary with the performance 
      data added to the database, and the id.

    Raise:
    - HTTPException (400): if performance profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check profile exists
    performance_profile_query = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == performance_profile_id,
        models.PerformanceProfile.aircraft_id.is_(None)
    ))
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {performance_profile_id} doesn't exist."
        )

    # Check profile is not repeated
    profile_exists = db_session.query(models.PerformanceProfile).filter(and_(
        not_(models.PerformanceProfile.id == performance_profile_id),
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.name == performance_data.performance_profile_name
    )).first()
    if profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile '{performance_data.performance_profile_name}' already exists."
        )

    # Check fuel type exists
    fuel_type_id_exists = db_session.query(models.FuelType).filter_by(
        id=performance_data.fuel_type_id).first()
    if not fuel_type_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provide a valid fuel type id"
        )

    # Update profile
    performance_profile_query.update({
        "name": performance_data.performance_profile_name,
        "fuel_type_id": performance_data.fuel_type_id,
        "is_complete": performance_data.is_complete
    })
    db_session.commit()

    # Return profile
    new_performance_profile = db_session.query(
        models.PerformanceProfile).filter_by(id=performance_profile_id).first()

    fuel_tanks = db_session.query(models.FuelTank).filter_by(
        performance_profile_id=performance_profile_id).all()

    fuel_capacity = sum([tank.fuel_capacity_gallons for tank in fuel_tanks])
    unusable_fuel = sum([tank.unusable_fuel_gallons for tank in fuel_tanks])

    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name,
        "fuel_capacity_gallons": fuel_capacity,
        "unusable_fuel_gallons": unusable_fuel,
        "created_at_utc": pytz.timezone('UTC').localize((new_performance_profile.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_performance_profile.last_updated))
    }


@router.delete("/fuel-type/{fuel_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fuel_type(
    fuel_type_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Fuel Type Endpoint.

    Parameters: 
    - fuel_type_id (int): fuel type id.

    Returns: None

    Raise:
    - HTTPException (400): if fuel type doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if fuel type exists.
    fuelt_type_query = db_session.query(models.FuelType).filter(
        models.FuelType.id == fuel_type_id)
    if not fuelt_type_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type with id {fuel_type_id} doesn't exists in the database."
        )

    # Delete fuel type
    deleted = fuelt_type_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_performance_profile(
    profile_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Performance Profile Endpoint.

    Parameters: 
    - profile_id (int): performance_profile id.

    Returns: None

    Raise:
    - HTTPException (400): if performance profile doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if performance profile exists
    profile_query = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id,
        models.PerformanceProfile.aircraft_id.is_(None)
    ))
    if profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} not found."
        )

    # Delete profile
    deleted = profile_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()
