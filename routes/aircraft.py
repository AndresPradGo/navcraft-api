"""
FastAPI aircraft router

This module defines the FastAPI aircraft endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from utils.functions import get_user_id_from_email

router = APIRouter(tags=["Aircraft"])


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.GetAircraftList]
)
async def get_aircraft_list(
    aircraft_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Aircraft List Endpoint.

    Parameters: 
    - aircraft_id (int optional): If provided, only 1 aircraft will be provided.

    Returns: 
    - List: list of dictionaries with aircraft data.

    Raise:
    - HTTPException (401): if user is not valid.
    - HTTPException (500): if there is a server error. 
    """

    # Get aircraft models
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    aircraft_models = db_session.query(models.Aircraft)\
        .filter(and_(
            models.Aircraft.owner_id == user_id,
            or_(
                not_(aircraft_id),
                models.Aircraft.id == aircraft_id
            )
        )).order_by(models.Aircraft.model).all()

    # Get profiles
    aircraft_ids = [aircraft.id for aircraft in aircraft_models]
    performance_profiles = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.aircraft_id.in_(aircraft_ids)
    ).all()

    # Organize aircraft list
    try:
        aircraft_list = [schemas.GetAircraftList(
            id=aircraft.id,
            make=aircraft.make,
            model=aircraft.model,
            abbreviation=aircraft.abbreviation,
            registration=aircraft.registration,
            profiles=[{
                "id": profile.id,
                "performance_profile_name": profile.name,
                "is_complete": profile.is_complete,
                "fuel_type_id": profile.fuel_type_id
            } for profile in performance_profiles if profile.aircraft_id == aircraft.id]
        ) for aircraft in aircraft_models]
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    return aircraft_list


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftReturn
)
async def post_new_aircraft(
    aircraft_data: schemas.AircraftData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Aircraft Endpoint.

    Parameters: 
    - aircraft_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if aircraft already exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

    # Check if aircraft already exists in database
    aircraft_exists = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.registration == aircraft_data.registration,
        models.Aircraft.owner_id == user_id
    )).first()
    if aircraft_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft {aircraft_data.registration} already registered."
        )

    # Post aircraft
    new_aircraft = models.Aircraft(
        make=aircraft_data.make,
        model=aircraft_data.model,
        abbreviation=aircraft_data.abbreviation,
        registration=aircraft_data.registration,
        owner_id=user_id
    )
    db_session.add(new_aircraft)
    db_session.commit()
    db_session.refresh(new_aircraft)

    return {**new_aircraft.__dict__}


@router.post(
    "/performance-profile/{aircraft_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
async def post_new_aircraft_performance_profile(
    aircraft_id: int,
    performance_data: schemas.PerformanceProfileData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Performance Profile Endpoint.

    Parameters: 
    - performance_data (dict): the data to be added.
    - aircraft_id (int): the aircraft id.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if user has permission
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    aircraft = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == aircraft_id,
        models.Aircraft.owner_id == user_id
    )).first()
    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aircraft not found."
        )

    # Check profile is not repeated
    profile_exists = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.aircraft_id == aircraft_id,
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
        aircraft_id=aircraft_id,
        fuel_type_id=performance_data.fuel_type_id,
        name=performance_data.performance_profile_name
    )
    db_session.add(new_performance_profile)
    db_session.commit()

    # Return profile
    db_session.refresh(new_performance_profile)
    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name
    }


@router.put(
    "/{aircraft_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftReturn
)
async def edit_aircraft(
    aircraft_id: int,
    aircraft_data: schemas.AircraftData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Aircraft Endpoint.

    Parameters: 
    - aircraft_id (int): aircraft id
    - aircraft_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if aircraft doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if aircraft exists
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    aircraft_query = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == aircraft_id,
        models.Aircraft.owner_id == user_id
    ))
    if aircraft_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft with id {aircraft_id} doesn't exist."
        )

    # Check if new aircraft data is repeated in
    aircraft_exists = db_session.query(models.Aircraft).filter(and_(
        not_(models.Aircraft.id == aircraft_id),
        models.Aircraft.registration == aircraft_data.registration,
    )).first()
    if aircraft_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft {aircraft_data.registration} already exists in the database."
        )

    # Update aircraft
    aircraft_query.update(aircraft_data.model_dump())
    db_session.commit()

    new_aircraft = db_session.query(
        models.Aircraft).filter_by(id=aircraft_id).first()
    return {**new_aircraft.__dict__}


@router.put(
    "/performance-profile/{performance_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
async def edit_aircraft_performance_profile(
    performance_profile_id: int,
    performance_data: schemas.PerformanceProfileData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Aircraft Performance Profile Endpoint.

    Parameters: 
    - performance_profile_id (int): performance profile id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if performance profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check profile exists
    performance_profile_query = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == performance_profile_id,
        models.PerformanceProfile.aircraft_id.isnot(None)
    ))
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {performance_profile_id} doesn't exist."
        )

    # Check is user has permission to edit this profile
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    user_is_aircraft_owner = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == performance_profile_query.first().aircraft_id,
        models.Aircraft.owner_id == user_id
    )).first()
    if user_is_aircraft_owner is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You do not have an aircraft with this profile"
        )

    # Check profile is not repeated
    profile_exists = db_session.query(models.PerformanceProfile).filter(and_(
        not_(models.PerformanceProfile.id == performance_profile_id),
        models.PerformanceProfile.aircraft_id == performance_profile_query.first().aircraft_id,
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
        "fuel_type_id": performance_data.fuel_type_id
    })
    db_session.commit()

    new_performance_profile = db_session.query(
        models.PerformanceProfile).filter_by(id=performance_profile_id).first()
    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name
    }


@router.delete("/performance-profile/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aircraft_performance_profile(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
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

    # Check if performance profile exists and user has permission.
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    profile_query = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id,
        models.PerformanceProfile.aircraft_id.isnot(None)
    ))
    if profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} not found."
        )
    user_is_aircraft_owner = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == profile_query.first().aircraft_id,
        models.Aircraft.owner_id == user_id
    )).first()
    if user_is_aircraft_owner is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aircraft with performance profile not found."
        )

    # Delete profile
    deleted = profile_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()


@router.delete("/{aircraft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aircraft(
    aircraft_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Aircraft Endpoint.

    Parameters: 
    - aircraft_id (int): aircraft id.

    Returns: None

    Raise:
    - HTTPException (400): if aircraft doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if aircraft exists and user has permission.
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    aircraft_query = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == aircraft_id,
        models.Aircraft.owner_id == user_id
    ))
    if aircraft_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft with id {aircraft_id} not found."
        )

    # Delete aircraft
    deleted = aircraft_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()
