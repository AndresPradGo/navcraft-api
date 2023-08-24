"""
FastAPI runways router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils.db import get_db

router = APIRouter(tags=["Runways"])


@router.get("/surfaces", status_code=status.HTTP_200_OK, response_model=List[schemas.RunwaySurfaceReturn])
async def get_all_runway_surfaces(
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Runway Surfaces Endpoint.

    Parameters: None

    Returns: 
    - list: list of runway syrface dictionaries.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    return db.query(models.RunwaySurface).all()


@router.post("/surface", status_code=status.HTTP_201_CREATED, response_model=schemas.RunwaySurfaceReturn)
async def post_runway_surface(
    surface_data: schemas.RunwaySurfaceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Runway Surface Endpoint.

    Parameters: 
    - surface_data (dict): the runway surface object to be added.

    Returns: 
    Dic: dictionary with the runway surface data.

    Raise:
    - HTTPException (400): if runway surface already exists.
    - HTTPException (500): if there is a server error. 
    """

    surface_exists = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.surface == surface_data.surface).first()

    if surface_exists:
        msg = f"{surface_data.surface} is already in the database, please enter a different surface, or edit the existing one."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    new_surface = models.User(
        surface=surface_data.surface,
        performance_level=surface_data.performance_level
    )
    db.add(new_surface)
    db.commit()
    db.refresh(new_surface)

    return new_surface


@router.put("/surface/{id}", status_code=status.HTTP_200_OK, response_model=schemas.RunwaySurfaceReturn)
async def edit_runway_surface(
    id,
    surface_data: schemas.RunwaySurfaceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Runway Surface Endpoint.

    Parameters: 
    - surface_data (dict): the runway surface object to be added.

    Returns: 
    Dic: dictionary with the runway surface data.

    Raise:
    - HTTPException (400): if runway surface already exists.
    - HTTPException (500): if there is a server error. 
    """
    surface_exists = db.query(models.RunwaySurface).filter(and_(
        models.RunwaySurface.surface == surface_data.surface,
        not_(models.RunwaySurface.id == id)
    )).first()

    if surface_exists:
        msg = f"{surface_data.surface} is already in the database, edit the existing record instead."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    surface_query = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == id
    )

    if not surface_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The surface ID provided does not exist in the database."
        )

    surface_query.update(surface_data.model_dump())
    db.commit()

    new_surface = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == id
    ).first()

    return new_surface
