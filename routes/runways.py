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
from sqlalchemy.exc import IntegrityError

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

    try:
        surfaces = db.query(models.RunwaySurface).all()
    except IntegrityError:
        raise common_responses.internal_server_error()

    return surfaces
