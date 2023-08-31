"""
FastAPI aircraft router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.db import get_db

router = APIRouter(tags=["Aircraft"])


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
