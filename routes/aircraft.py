"""
FastAPI aircraft router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.db import get_db

router = APIRouter(tags=["Aircraft"])


@router.get("/fuel-type", status_code=status.HTTP_200_OK, response_model=List[schemas.FuelTypeReturn])
async def get_fuel_types(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Fuel Types Endpoint.

    Parameters: 
    - id (int): fuel type id, for returning only 1 fuel type. If 0 or none, 
      it returns all entries. If id doesn't exist, it returns an empty list

    Returns: 
    - List: list of dictionaries with the fuel types.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    fuel_types = db.query(models.FuelType).filter(or_(
        not_(id),
        models.FuelType.id == id
    )).all()

    return [fuel_type.__dict__ for fuel_type in fuel_types]


@router.get("/make", status_code=status.HTTP_200_OK, response_model=List[schemas.AircraftMakeReturn])
async def get_aircraft_manufacturers(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Aircraft Manufacturers Endpoint.

    Parameters: 
    - id (int): fuel type id, for returning only 1 manufacturer. If 0 or none, 
      it returns all entries. If id doesn't exist, it returns an empty list

    Returns: 
    - List: list of dictionaries with the manufacturers' data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    manufacturers = db.query(models.AircraftMake).filter(or_(
        not_(id),
        models.AircraftMake.id == id
    )).all()

    return [manufacturer.__dict__ for manufacturer in manufacturers]


@router.post("/fuel-type", status_code=status.HTTP_201_CREATED, response_model=schemas.FuelTypeReturn)
async def post_new_fuel_type(
    fuel_type: schemas.FuelTypeData,
    db: Session = Depends(get_db),
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
    fuelt_type_exists = db.query(models.FuelType).filter_by(
        name=fuel_type.name).first()
    if fuelt_type_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{fuel_type.name} fuel already exists in the database."
        )
    # Add fuel type to database
    new_fuel_type = models.FuelType(**fuel_type.model_dump())
    db.add(new_fuel_type)
    db.commit()

    # Return fuel type data
    db.refresh(new_fuel_type)

    return new_fuel_type


@router.post("/make", status_code=status.HTTP_201_CREATED, response_model=schemas.AircraftMakeReturn)
async def post_new_aircraft_manufacturer(
    make_data: schemas.AircraftMakeData,
    db: Session = Depends(get_db),
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
    make_exists = db.query(models.AircraftMake).filter_by(
        name=make_data.name).first()
    if make_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{make_data.name} already exists in the database."
        )
    # Add manufacturer to database
    new_make = models.AircraftMake(**make_data.model_dump())
    db.add(new_make)
    db.commit()

    # Return manufacturer data
    db.refresh(new_make)
    return new_make


@router.put("/fuel-type/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.FuelTypeReturn)
async def edit_fuel_type(
    id: int,
    fuel_type: schemas.FuelTypeData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Fuel Type Endpoint.

    Parameters: 
    - id (int): fuel type id.
    - fuel_type (dict): the fuel type data to be added.

    Returns: 
    - Dic: dictionary with the new fuel type data.

    Raise:
    - HTTPException (400): if fuel type doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check id is valid
    fuelt_type_query = db.query(models.FuelType).filter(
        models.FuelType.id == id)

    if not fuelt_type_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type with id {id} doesn't exists in the database."
        )

    # Check if fuel type with same name exists
    fuelt_type_exists = db.query(models.FuelType).filter(and_(
        models.FuelType.name == fuel_type.name,
        not_(models.FuelType.id == id)
    )).first()
    if fuelt_type_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{fuel_type.name} fuel already exists in the database."
        )
    # Edit fuel type
    fuelt_type_query.update(fuel_type.model_dump())
    db.commit()

    # Return fuel type data
    return fuelt_type_query.first().__dict__


@router.put("/make/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.AircraftMakeReturn)
async def edit_aircraft_manufacturer(
    id: int,
    make_data: schemas.AircraftMakeData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Aircraft Manufacturer Endpoint.

    Parameters: 
    - id (int): Aircraft Manufacturer id.
    - make_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the new manufacturer data.

    Raise:
    - HTTPException (400): if manufacturer id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check id is valid
    make_query = db.query(models.AircraftMake).filter(
        models.AircraftMake.id == id)

    if not make_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer with id {id} doesn't exists in the database."
        )

    # Check if manufacturer with same name exists
    make_exists = db.query(models.AircraftMake).filter(and_(
        models.AircraftMake.name == make_data.name,
        not_(models.AircraftMake.id == id)
    )).first()
    if make_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{make_data.name} already exists in the database."
        )
    # Edit manufacturer
    make_query.update(make_data.model_dump())
    db.commit()

    # Return manufacturer data
    return make_query.first().__dict__


@router.delete("/fuel-type/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fuel_type(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Fuel Type Endpoint.

    Parameters: 
    - id (int): fuel type id.

    Returns: None

    Raise:
    - HTTPException (400): if fuel type doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if fuel type exists.
    fuelt_type_query = db.query(models.FuelType).filter(
        models.FuelType.id == id)
    if not fuelt_type_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type with id {id} doesn't exists in the database."
        )

    # Delete fuel type
    deleted = fuelt_type_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db.commit()


@router.delete("/make/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aircraft_manufacturer(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Aircraft Manufaturer Endpoint.

    Parameters: 
    - id (int): manufacturer id.

    Returns: None

    Raise:
    - HTTPException (400): if manufacturer id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if manufacturer exists.
    make_query = db.query(models.AircraftMake).filter(
        models.AircraftMake.id == id)

    if not make_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer with id {id} doesn't exists in the database."
        )

    # Delete manufacturer
    deleted = make_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db.commit()
