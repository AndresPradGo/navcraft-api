"""
FastAPI runways router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import text, and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
from queries import user_queries
import schemas
from utils.db import get_db
from utils import common_responses

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
async def post_unofficial_waypoint(
    surface_data: schemas.RunwaySurfaceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Runway Surface Endpoint.

    Parameters: 
    - waypoint (dict): the runway surface object to be added.

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
