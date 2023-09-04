"""
FastAPI aircraft models router

This module defines the FastAPI aircraft models endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import and_, or_, not_, func
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db

router = APIRouter(tags=["Aircraft Models"])


@router.get(
    "/fuel-type",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.FuelTypeReturn]
)
async def get_fuel_types(
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
    - List: list of dictionaries with the fuel types.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    return db_session.query(models.FuelType).filter(or_(
        not_(fuel_type_id),
        models.FuelType.id == fuel_type_id
    )).order_by(models.FuelType.name).all()


@router.get(
    "/make",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.AircraftMakeReturn]
)
async def get_aircraft_manufacturers(
    aircraft_make_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Aircraft Manufacturers Endpoint.

    Parameters: 
    - aircraft_make_id (int): fuel type id, for returning only 1 manufacturer. If 0 or none, 
      it returns all entries. If id doesn't exist, it returns an empty list

    Returns: 
    - List: list of dictionaries with the manufacturers' data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    return db_session.query(models.AircraftMake).filter(or_(
        not_(aircraft_make_id),
        models.AircraftMake.id == aircraft_make_id
    )).order_by(models.AircraftMake.name).all()


@router.post(
    "/fuel-type",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTypeReturn
)
async def post_new_fuel_type(
    fuel_type: schemas.FuelTypeData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Fuel Type Endpoint.

    Parameters: 
    - fuel_type (dict): the fuel type data to be added.

    Returns: 
    - Dic: dictionary with the fuel type data added to the database, and the id.

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
    "/make",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftMakeReturn
)
async def post_new_aircraft_manufacturer(
    make_data: schemas.AircraftMakeData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Aircraft Manufacturer Endpoint.

    Parameters: 
    - make_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if manufacturer already exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if manufacturer already exists in database
    make_exists = db_session.query(models.AircraftMake).filter_by(
        name=make_data.name).first()
    if make_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{make_data.name} already exists in the database."
        )
    # Add manufacturer to database
    new_make = models.AircraftMake(**make_data.model_dump())
    db_session.add(new_make)
    db_session.commit()

    # Return manufacturer data
    db_session.refresh(new_make)
    return new_make


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftModelOfficialPostReturn
)
async def post_new_aircraft_model(
    model_data: schemas.AircraftModelOfficialPostData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Aircraft Model Endpoint.

    Parameters: 
    - model_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if model already exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if model already exists in database
    model_exists = db_session.query(models.AircraftModel).filter(
        func.upper(models.AircraftModel.model) == func.upper(model_data.model)).first()
    if model_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{model_data.model} already exists in the database."
        )

    # Check manufacturer exists
    make_id_exists = db_session.query(models.AircraftMake).filter_by(
        id=model_data.make_id).first()
    if not make_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer ID {model_data.make_id} doesn't exist."
        )

    # Check fuel type exists
    fuel_type_id_exists = db_session.query(models.FuelType).filter_by(
        id=model_data.fuel_type_id).first()
    if not fuel_type_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type ID {model_data.fuel_type_id} doesn't exist."
        )

    # Post aircraft model
    new_model = models.AircraftModel(
        model=model_data.model,
        code=model_data.code,
        make_id=model_data.make_id,
    )
    db_session.add(new_model)
    db_session.commit()
    db_session.refresh(new_model)
    new_model_dict = {**new_model.__dict__}

    # Post performance profile
    new_performance_profile = models.PerformanceProfile(
        model_id=new_model.id,
        fuel_type_id=model_data.fuel_type_id,
        name=model_data.performance_profile_name,
        is_complete=model_data.is_complete
    )
    db_session.add(new_performance_profile)
    db_session.commit()
    db_session.refresh(new_performance_profile)

    return {
        **new_model_dict,
        "fuel_type_id": new_performance_profile.fuel_type_id,
        "performance_profile_name": new_performance_profile.name,
        "performance_profile_id": new_performance_profile.id,
        "is_complete": new_performance_profile.is_complete
    }


@router.post(
    "/performance/{model_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfilePostReturn
)
async def post_new_aircraft_model_performance_profile(
    model_id: int,
    performance_data: schemas.PerformanceProfilePostData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Model Performance Profile Endpoint.

    Parameters: 
    - model_id (int): model id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if model doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check model exists
    model = db_session.query(
        models.AircraftModel).filter_by(id=model_id).first()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with id {model_id} doesn't exist."
        )

    # Check profile is not repeated
    profile_exists = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.model_id == model_id,
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
        model_id=model_id,
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
        "performance_profile_name": new_performance_profile.name
    }


@router.put(
    "/fuel-type/{fuel_type_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTypeReturn
)
async def edit_fuel_type(
    fuel_type_id: int,
    fuel_type: schemas.FuelTypeData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Fuel Type Endpoint.

    Parameters: 
    - fuel_type_id (int): fuel type id.
    - fuel_type (dict): the fuel type data to be added.

    Returns: 
    - Dic: dictionary with the new fuel type data.

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
    "/make/{aircraft_make_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftMakeReturn
)
async def edit_aircraft_manufacturer(
    aircraft_make_id: int,
    make_data: schemas.AircraftMakeData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Aircraft Manufacturer Endpoint.

    Parameters: 
    - aircraft_make_id (int): Aircraft Manufacturer id.
    - make_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the new manufacturer data.

    Raise:
    - HTTPException (400): if manufacturer id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check id is valid
    make_query = db_session.query(models.AircraftMake).filter(
        models.AircraftMake.id == aircraft_make_id)

    if not make_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer with id {aircraft_make_id} doesn't exists in the database."
        )

    # Check if manufacturer with same name exists
    make_exists = db_session.query(models.AircraftMake).filter(and_(
        models.AircraftMake.name == make_data.name,
        not_(models.AircraftMake.id == aircraft_make_id)
    )).first()
    if make_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{make_data.name} already exists in the database."
        )
    # Edit manufacturer
    make_query.update(make_data.model_dump())
    db_session.commit()

    # Return manufacturer data
    return make_query.first().__dict__


@router.put(
    "/{model_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftModelOfficialBaseReturn
)
async def edit_aircraft_model(
    model_id: int,
    model_data: schemas.AircraftModelOfficialBaseData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Aircraft Model Endpoint.

    Parameters: 
    - model_id (int): model id
    - model_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if model doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if model exists
    model_query = db_session.query(models.AircraftModel).filter_by(id=model_id)
    if model_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with id {model_id} doesn't exist."
        )

    # Check if new model data is repeated in
    model_exists = db_session.query(models.AircraftModel).filter(and_(
        not_(models.AircraftModel.id == model_id),
        func.upper(models.AircraftModel.model) == func.upper(model_data.model),
    )).first()
    if model_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{model_data.model} already exists in the database."
        )

    # Check manufacturer exists
    make_id_exists = db_session.query(models.AircraftMake).filter_by(
        id=model_data.make_id).first()
    if not make_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer ID {model_data.make_id} doesn't exist."
        )

    # Update aircraft model
    model_query.update(model_data.model_dump())
    db_session.commit()

    new_model = db_session.query(
        models.AircraftModel).filter_by(id=model_id).first()
    return {**new_model.__dict__}


@router.put(
    "/performance/{performance_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfilePostReturn
)
async def edit_aircraft_model_performance_profile(
    performance_profile_id: int,
    performance_data: schemas.PerformanceProfilePostData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Model Performance Profile Endpoint.

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
    performance_profile_query = db_session.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        ))
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {performance_profile_id} doesn't exist."
        )

    # Check profile is not repeated
    profile_exists = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.model_id == performance_profile_query.first().model_id,
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
            detail=f"Fuel type ID {performance_data.fuel_type_id} doesn't exist."
        )

    # Update profile
    performance_profile_query.update({
        "name": performance_data.performance_profile_name,
        "fuel_type_id": performance_data.fuel_type_id,
        "is_complete": performance_data.is_complete
    })
    db_session.commit()

    new_performance_profile = db_session.query(
        models.PerformanceProfile).filter_by(id=performance_profile_id).first()
    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name
    }


@router.delete("/fuel-type/{fuel_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fuel_type(
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


@router.delete("/make/{aircraft_make_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aircraft_manufacturer(
    aircraft_make_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Aircraft Manufaturer Endpoint.

    Parameters: 
    - aircraft_make_id (int): manufacturer id.

    Returns: None

    Raise:
    - HTTPException (400): if manufacturer id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if manufacturer exists.
    make_query = db_session.query(models.AircraftMake).filter(
        models.AircraftMake.id == aircraft_make_id)

    if not make_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer with id {aircraft_make_id} doesn't exists in the database."
        )

    # Delete manufacturer
    deleted = make_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()
