"""
FastAPI flights router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
import re
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from utils.functions import clean_string

router = APIRouter(tags=["Flights"])


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.FlightStatusReturn]
)
async def get_all_flight_status(
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Flight Status Endpoint.

    Returns: 
    - list: list of flight status.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    return [
        status.__dict__ for status in db_session.query(models.FlightStatus).all()
    ]


@router.post(
    "/status",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FlightStatusReturn
)
async def post_flight_status(
    flight_status: str,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Flight Status Endpoint.

    Parameters: 
    - status (dict): the flight status to be added.

    Returns: 
    - Dic: dictionary with the flight status and id.

    Raise:
    - HTTPException (400): if flight status already exists, or it
      contains characters other than letters, hyphen and white space.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    pattern = r'^[-A-Za-z ]*$'
    status_matches_pattern = re.match(pattern, flight_status) is not None
    if not status_matches_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use only letters, hyphens, and spaces in the flight status."
        )

    clean_status = clean_string(flight_status)

    already_exists = db_session.query(models.FlightStatus).filter_by(
        status=clean_status).first()
    if already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight status already exists."
        )

    new_flight_status = models.FlightStatus(status=clean_status)
    db_session.add(new_flight_status)
    db_session.commit()
    db_session.refresh(new_flight_status)

    return new_flight_status


@router.delete("/status/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aerodrome_status(
    status_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Flight Status.

    Parameters: 
    status_id (int): status id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    status_query = db_session.query(
        models.FlightStatus).filter_by(id=status_id)

    if not status_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The flight status you're trying to delete is not in the database."
        )

    deleted = status_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()
