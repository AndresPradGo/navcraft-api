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
    - id (int): fuel type id, for returning only 1.

    Returns: 
    - List: list of dictionaries with the fuel types.

    Raise:
    - HTTPException (400): if fuel type doesn't exists.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    fuel_types = db.query(models.FuelType).filter(or_(
        not_(id),
        models.FuelType.id == id
    )).all()

    return [fuel_type.__dict__ for fuel_type in fuel_types]


@router.post("/fuel-type", status_code=status.HTTP_201_CREATED, response_model=schemas.FuelTypeReturn)
async def post_fuel_type(
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


@router.delete("/fuel-type/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_fuel_type(
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
