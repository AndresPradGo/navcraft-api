"""
FastAPI aircraft router

This module defines the FastAPI aircraft endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import ValidationError
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
    unload_aircraft,
    create_empty_tanks
)

router = APIRouter(tags=["Aircraft"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.GetAircraftList]
)
def get_aircraft_list(
    aircraft_id: Optional[int] = 0,
    complete_only: bool = False,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Aircraft List Endpoint.

    Parameters: 
    - aircraft_id (int optional): If provided, only 1 aircraft will be returned.
    - complete_only (bool): If true, only return aircraft with a preferred profile.

    Returns: 
    - List[dict[GetAircraftList]]: list of dictionaries with aircraft data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get aircraft models
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
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
            created_at_utc=pytz.timezone(
                'UTC').localize((aircraft.created_at)),
            last_updated_utc=pytz.timezone(
                'UTC').localize((aircraft.last_updated)),
            profiles=[{
                "id": profile.id,
                "performance_profile_name": profile.name,
                "is_complete": profile.is_complete,
                "fuel_type_id": profile.fuel_type_id,
                "is_preferred": profile.is_preferred,
                "created_at_utc": pytz.timezone('UTC').localize((profile.created_at)),
                "last_updated_utc": pytz.timezone('UTC').localize((profile.last_updated))
            } for profile in performance_profiles if profile.aircraft_id == aircraft.id]
        ) for aircraft in aircraft_models]
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    # Filter Aircraft
    if complete_only:
        filtered_aircraft = [a for a in aircraft_list if any(
            {p.is_preferred for p in a.profiles})]
    else:
        filtered_aircraft = aircraft_list

    return filtered_aircraft


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftReturn
)
def post_new_aircraft(
    aircraft_data: schemas.AircraftData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Aircraft Endpoint.

    Parameters: 
    - aircraft_data (dict[AircraftData]): the aircraft data to be added.

    Returns: 
    - dic[AircraftReturn]: dictionary with the aircraft data added to the database, and the id.

    Raise:
    - HTTPException (400): if aircraft already exists, or data is wrong.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)

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

    return {
        **new_aircraft.__dict__,
        "created_at_utc": pytz.timezone('UTC').localize((new_aircraft.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_aircraft.last_updated))
    }


@router.post(
    "/performance-profile/{aircraft_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
def post_new_aircraft_performance_profile(
    aircraft_id: int,
    performance_data: schemas.PerformanceProfileData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Performance Profile Endpoint.

    Parameters: 
    - aircraft_id (int): the aircraft id.
    - performance_data (dict[PerformanceProfileData]): 
      the perforamnce profile data to be added.

    Returns: 
    - dic[PerformanceProfileReturn]: dictionary with the 
      performance profile data added to the database, and the id.

    Raise:
    - HTTPException (400): if data is wrong.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check if user has permission
    user_id = get_user_id_from_email(
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
    aircraft_profiles = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.aircraft_id == aircraft_id,
    ).all()

    if len(aircraft_profiles) >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This aircraft already has 3 profiles."
        )

    profile_exists = len([
        profile.name for profile in aircraft_profiles
        if profile.name == performance_data.performance_profile_name
    ]) > 0
    if profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'"{performance_data.performance_profile_name}" Profile already exists.'
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
        is_preferred=False,
        fuel_type_id=performance_data.fuel_type_id,
        name=performance_data.performance_profile_name,
        is_complete=False
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


@router.post(
    "/performance-profile/{aircraft_id}/{model_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
def post_new_aircraft_performance_profile_from_model(
    aircraft_id: int,
    model_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Performance Profile Frpm Model Endpoint.

    Parameters: 
    - aircraft_id (int): the aircraft id.
    - model_id (int): the model id.

    Returns: 
    - dic[PerformanceProfileReturn]: dictionary with the
      performance profile data added to the database, and the id.

    Raise:
    - HTTPException (400): if data is wrong.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Check if user has permission
    user_id = get_user_id_from_email(
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

    # Get model performance profile
    model_profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.id == model_id,
        models.PerformanceProfile.is_complete.is_(True)
    )).first()
    if model_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model ID."
        )

    # define reusable function to pop key-value pairs form dictionaries
    def remove_key_value_pairs(dictionary: Dict[str, Any], keys: List[str]):
        """
        This function removes a list of keys form a dictionary
        """
        keys.append('id')
        keys.append('_sa_instance_state')
        keys.append('created_at')
        keys.append('last_updated')

        for key in keys:
            if key in dictionary:
                dictionary.pop(key)

        return dictionary

    # Check profile is not repeated
    aircraft_profiles = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.aircraft_id == aircraft_id
    ).all()

    if len(aircraft_profiles) >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This aircraft already has 3 profiles."
        )

    # Change Profile Name if it exists
    profile_values = remove_key_value_pairs(
        dictionary=model_profile.__dict__,
        keys=["aircraft_id"]
    )

    profile_exists = len([
        profile.name for profile in aircraft_profiles
        if profile.name == profile_values["name"]
    ]) > 0
    copies = 1
    original_name = profile_values["name"]

    while profile_exists:
        profile_values["name"] = f"{original_name} ({copies})"
        profile_exists = len([
            profile.name for profile in aircraft_profiles
            if profile.name == profile_values["name"]
        ]) > 0

        copies += 1

    completed_aircraft_profiles = [
        profile for profile in aircraft_profiles if profile.is_complete
    ]
    is_preferred = len(completed_aircraft_profiles) == 0

    # Post profile
    new_performance_profile = models.PerformanceProfile(**{
        **profile_values,
        "aircraft_id": aircraft_id,
        "is_preferred": is_preferred,
        "is_complete": True
    })
    db_session.add(new_performance_profile)
    db_session.commit()
    db_session.refresh(new_performance_profile)
    new_profile_dict = {**new_performance_profile.__dict__}
    new_profile_id = new_performance_profile.id

    # Add weight and balance profiles
    wb_query_results = db_session.query(models.WeightBalanceProfile)\
        .filter_by(performance_profile_id=model_id).all()
    for row in wb_query_results:
        limits_query = db_session.query(models.WeightBalanceLimit)\
            .filter_by(weight_balance_profile_id=row.id)

        new_weight_balance = models.WeightBalanceProfile(**{
            **remove_key_value_pairs(
                dictionary=row.__dict__,
                keys=["performance_profile_id"]
            ),
            "performance_profile_id": new_profile_id
        })
        db_session.add(new_weight_balance)
        db_session.commit()
        db_session.refresh(new_weight_balance)

        limits_to_add = [models.WeightBalanceLimit(**{
            **remove_key_value_pairs(
                dictionary=row.__dict__,
                keys=["weight_balance_profile_id"]
            ),
            "weight_balance_profile_id": new_weight_balance.id
        }) for row in limits_query.all()]
        db_session.add_all(limits_to_add)
        db_session.commit()

    # Define reusable function to add performance data
    def add_performance_models(models_list: List[Any]):
        """
        This function copies the performance data from the model performance profile,
        and adds it to the new performance profile.
        """
        for model in models_list:
            query_results = db_session.query(model)\
                .filter_by(performance_profile_id=model_id).all()
            rows_to_add = [model(**{
                **remove_key_value_pairs(
                    dictionary=row.__dict__,
                    keys=["performance_profile_id"]
                ),
                "performance_profile_id": new_profile_id
            }) for row in query_results]
            db_session.add_all(rows_to_add)

    # Add all other performance data tables
    add_performance_models([
        models.BaggageCompartment,
        models.SeatRow,
        models.FuelTank,
        models.SurfacePerformanceDecrease,
        models.TakeoffPerformance,
        models.LandingPerformance,
        models.ClimbPerformance,
        models.CruisePerformance
    ])

    db_session.commit()
    create_empty_tanks(
        profile_id=new_profile_id,
        db_session=db_session
    )

    # Return profile data
    fuel_tanks = db_session.query(models.FuelTank).filter_by(
        performance_profile_id=new_profile_id).all()

    fuel_capacity = sum([tank.fuel_capacity_gallons for tank in fuel_tanks])
    unusable_fuel = sum([tank.unusable_fuel_gallons for tank in fuel_tanks])

    return {
        **new_profile_dict,
        "performance_profile_name": new_profile_dict["name"],
        "fuel_capacity_gallons": fuel_capacity,
        "unusable_fuel_gallons": unusable_fuel,
        "created_at_utc": pytz.timezone('UTC').localize((new_profile_dict["created_at"])),
        "last_updated_utc": pytz.timezone('UTC').localize((new_profile_dict["last_updated"]))
    }


@router.put(
    "/{aircraft_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftReturn
)
def edit_aircraft(
    aircraft_id: int,
    aircraft_data: schemas.AircraftData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Aircraft Endpoint.

    Parameters: 
    - aircraft_id (int): aircraft id
    - aircraft_data (dict[AircraftData]): the data to be added.

    Returns: 
    - dic[AircraftReturn]: dictionary with the aircraft data added to the 
      database, and the id.

    Raise:
    - HTTPException (400): if aircraft doesn't exists, or data is wrong.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check if aircraft exists
    user_id = get_user_id_from_email(
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
    return {
        **new_aircraft.__dict__,
        "created_at_utc": pytz.timezone('UTC').localize((new_aircraft.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_aircraft.last_updated))
    }


@router.put(
    "/performance-profile/{performance_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
def edit_aircraft_performance_profile(
    performance_profile_id: int,
    performance_data: schemas.PerformanceProfileData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Aircraft Performance Profile Endpoint.

    Parameters: 
    - performance_profile_id (int): performance profile id.
    - performance_data (dict[PerformanceProfileData]): the 
      perforamnce profile data to be added.

    Returns: 
    - dic[PerformanceProfileReturn]: dictionary with the data added 
      to the database, and the id.

    Raise:
    - HTTPException (400): if performance profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not authenticated.
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
    user_id = get_user_id_from_email(
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


@router.put(
    "/performance-profile/make-preferred/{performance_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
def make_aircraft_performance_profile_preferred_profile(
    performance_profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Make Aircraft Performance Profile, Preferred Profile Endpoint.

    Parameters: 
    - performance_profile_id (int): performance profile id.

    Returns: 
    - dic[PerformanceProfileReturn]: dictionary with the performance profile data.

    Raise:
    - HTTPException (400): if performance profile doesn't exists.
    - HTTPException (401): if user is not authenticated.
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

    # Check if user has permission to edit this profile
    aircraft_id = performance_profile_query.first().aircraft_id
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    user_is_aircraft_owner = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == aircraft_id,
        models.Aircraft.owner_id == user_id
    )).first()
    if user_is_aircraft_owner is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You do not have an aircraft with this profile"
        )

    # Check if profiles is complete
    if not performance_profile_query.first().is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete the profile before making it preferred."
        )
    # Make all aircraft profiles not preferred
    preferred_profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.aircraft_id == aircraft_id,
        models.PerformanceProfile.is_preferred.is_(True)
    )).first()
    if preferred_profile is not None:
        unload_aircraft(profile_id=preferred_profile.id, db_session=db_session)

    db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.aircraft_id == aircraft_id
    ).update({"is_preferred": False})

    # Update profile
    performance_profile_query.update({"is_preferred": True})
    db_session.commit()
    create_empty_tanks(
        profile_id=performance_profile_id,
        db_session=db_session
    )

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


@router.delete("/performance-profile/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aircraft_performance_profile(
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
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check if performance profile exists and user has permission.
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id,
        models.PerformanceProfile.aircraft_id.isnot(None)
    )).first()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} not found."
        )
    profile_was_preferred = profile.is_preferred

    # Find aircraft linked to user
    aircraft = db_session.query(models.Aircraft).filter(and_(
        models.Aircraft.id == profile.aircraft_id,
        models.Aircraft.owner_id == user_id
    )).first()
    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aircraft with performance profile not found."
        )

    aircraft_id = aircraft.id

    # Delete profile
    deleted = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id,
        models.PerformanceProfile.aircraft_id.isnot(None)
    )).delete()

    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()

    if profile_was_preferred:
        complete_profile = db_session.query(models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.aircraft_id == aircraft_id,
            models.PerformanceProfile.is_complete.is_(True)
        )).first()
        if complete_profile is not None:
            complete_profile_id = complete_profile.id
            create_empty_tanks(
                profile_id=complete_profile_id, db_session=db_session
            )
            db_session.query(models.PerformanceProfile).filter(
                models.PerformanceProfile.id == complete_profile_id
            ).update({"is_preferred": True})

            db_session.commit()


@router.delete("/{aircraft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aircraft(
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
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check if aircraft exists and user has permission.
    user_id = get_user_id_from_email(
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
