"""
FastAPI waypoints router

This module defines the FastAPI waipoints router.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
from utils.db import get_db

router = APIRouter(tags=["Waypoints"])


async def post_waypoint(waypoint: schemas.Waypoint, db: Session):
    """
    This function checks if the waypoint passed as a parameter
    already exists in the database, and adds it to the database, 
    or returns and error response.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint to be added to the database.
    - db (sqlalchemy Session): database session.

    Returns: Object with the details of the response. 
    """

    try:
        exists = db.query(models.Waypoint).filter_by(
            code=waypoint.code).first()
    except IntegrityError:
        return {
            "body": {
                "msg": "Something went wrong, we'll look into it ASAP, please try again latter."
            },
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        }

    if exists:
        try:
            is_airport = db.query(models.Aerodrome).filter_by(
                id=exists.id).first()
        except IntegrityError:
            return {
                "body": {
                    "msg": "Something went wrong, we'll look into it ASAP, please try again latter."
                },
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }

        if is_airport:
            msg = f"Aerodrome with code {waypoint.code} already exists. Try using a different code."
        else:
            msg = f"Waypoint with code {waypoint.code} already exists. Try using a different code."

        return {"body": {"msg": msg}, "status_code": status.HTTP_400_BAD_REQUEST}

    new_waypoint = models.Waypoint(
        code=waypoint.code,
        name=waypoint.name,
        is_official=waypoint.is_official,
        lat_degrees=waypoint.lat_degrees,
        lat_minutes=waypoint.lat_minutes,
        lat_seconds=waypoint.lat_seconds,
        lat_direction=waypoint.lat_direction,
        lon_degrees=waypoint.lon_degrees,
        lon_minutes=waypoint.lon_minutes,
        lon_seconds=waypoint.lon_seconds,
        lon_direction=waypoint.lon_direction,
        magnetic_variation=waypoint.magnetic_variation
    )

    try:
        db.add(new_waypoint)
        db.commit()
        db.refresh(new_waypoint)
    except IntegrityError:
        return {
            "body": {"msg": "Something went wrong, we'll look into it ASAP, please try again latter."},
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        }

    return {"body": new_waypoint, "status_code": status.HTTP_201_CREATED}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def post_waypoint_endpoint(
    waypoint: schemas.Waypoint,
    response: Response,
    db: Session = Depends(get_db)
) -> {}:
    """
    Post Waypoint Endpoint.

    Parameters: 
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data, or with details of an error response.
    """

    result = await post_waypoint(waypoint=waypoint, db=db)

    if "status_code" in result:
        response.status_code = result["status_code"]

    return result["body"]
