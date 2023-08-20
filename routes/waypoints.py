"""
FastAPI waypoints router

This module defines the FastAPI waipoints router.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, Response, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
from utils.db import get_db
from utils import common_responses

router = APIRouter(tags=["Waypoints"])


async def post_waypoint(waypoint: schemas.Waypoint, db: Session):
    """
    This function checks if the waypoint passed as a parameter
    already exists in the database, and adds it to the database, 
    or returns and error response.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint to be added to the database.
    - db (sqlalchemy Session): database session.

    Returns: 
    dict: Object with the added waypoint 

    Raise:
    HTTPException (400): if waypoint already exists.
    HTTPException (500): if there is a server error. 
    """

    try:
        exists = db.query(models.Waypoint).filter_by(
            code=waypoint.code).first()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=common_responses.internal_server_error()
        )

    if exists:
        try:
            is_aerodrome = db.query(models.Aerodrome).filter_by(
                waypoint_id=exists.id).first()

        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=common_responses.internal_server_error()
            )

        msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} with code {waypoint.code} already exists. Try using a different code."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    try:
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
            magnetic_variation=waypoint.magnetic_variation,
            creator_id=waypoint.creator_id
        )

        db.add(new_waypoint)
        db.commit()
        db.refresh(new_waypoint)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=common_responses.internal_server_error()
        )

    return new_waypoint


@router.get("/", status_code=status.HTTP_200_OK)
async def get_waypoints(db: Session = Depends(get_db)):
    """
    Get Waypoints Endpoint.

    Parameters: None

    Returns: 
    list: list of waypoint dictionaries.

    Raise:
    HTTPException (500): if there is a server error. 
    """

    query = text("SELECT waypoint_id FROM aerodromes")

    try:
        aerodromes_ids = [id[0] for id in db.execute(query).fetchall()]
        waypoints = db.query(models.Waypoint).filter(
            models.Waypoint.id.not_in(aerodromes_ids)).all()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=common_responses.internal_server_error()
        )

    return waypoints


@router.get("/aerodromes", status_code=status.HTTP_200_OK)
async def get_aerodromes(db: Session = Depends(get_db)):
    """
    Get Aerodromes Endpoint.

    Parameters: None

    Returns: 
    list: list of aerodrome dictionaries.

    Raise:
    HTTPException (500): if there is a server error. 
    """

    a = models.Aerodrome
    w = models.Waypoint

    try:
        query_results = db.query(w, a).join(a, w.id == a.waypoint_id).all()
        aerodromes = [
            {**w.__dict__, **a.__dict__, "waypoint_id": None} for w, a in query_results
        ]
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=common_responses.internal_server_error()
        )

    return aerodromes


@router.post("/", status_code=status.HTTP_201_CREATED)
async def post_waypoint_endpoint(
    waypoint: schemas.Waypoint,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Post Waypoint Endpoint.

    Parameters: 
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    HTTPException (400): if waypoint already exists.
    HTTPException (500): if there is a server error. 
    """

    try:
        result = await post_waypoint(waypoint=waypoint, db=db)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return result


@router.post("/aerodrome", status_code=status.HTTP_201_CREATED)
async def post_aerodrome_endpoint(
    waypoint: schemas.Waypoint,
    aerodrome: schemas.Aerodrome,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Post Aerodrome Endpoint.

    Parameters: 
    - waypoint (dict): the waypoint object to be added.
    - aerodrome (dict): the aerodrome object to be added.

    Returns: 
    Dic: dictionary with the aerodrome and waypoint data.

    Raise:
    HTTPException (400): if waypoint already exists.
    HTTPException (500): if there is a server error. 
    """

    try:
        waypoint_result = await post_waypoint(waypoint=waypoint, db=db)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    try:
        new_aerodrome = models.Aerodrome(
            waypoint_id=waypoint_result.id,
            has_taf=aerodrome.has_taf,
            has_metar=aerodrome.has_metar,
            has_fds=aerodrome.has_fds,
            elevation_ft=aerodrome.elevation_ft
        )

        db.add(new_aerodrome)
        db.commit()
        db.refresh(new_aerodrome)
        db.refresh(waypoint_result)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=common_responses.internal_server_error()
        )

    aerodrome_dict = {**new_aerodrome.__dict__, **waypoint_result.__dict__}
    del aerodrome_dict["waypoint_id"]

    return aerodrome_dict
