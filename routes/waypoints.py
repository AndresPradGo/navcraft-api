"""
FastAPI waypoints router

This module defines the FastAPI waipoints router.

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

router = APIRouter(tags=["Waypoints"])


async def post_waypoint(waypoint: schemas.WaypointData, db: Session, creator_id: int, official: bool):
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
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    db_waypoint_code = f"{waypoint.code}{'' if official else f'@{creator_id}'}"

    try:
        exists = db.query(models.Waypoint).filter(
            models.Waypoint.code == db_waypoint_code).first()
    except IntegrityError:
        raise common_responses.internal_server_error()

    if exists:
        try:
            is_aerodrome = db.query(models.Aerodrome).filter_by(
                waypoint_id=exists.id).first()

        except IntegrityError:
            raise common_responses.internal_server_error()

        msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} with code {waypoint.code} already exists. Try using a different code."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    try:
        new_waypoint = models.Waypoint(
            code=db_waypoint_code,
            name=waypoint.name,
            is_official=official,
            lat_degrees=waypoint.lat_degrees,
            lat_minutes=waypoint.lat_minutes,
            lat_seconds=waypoint.lat_seconds,
            lat_direction=waypoint.lat_direction,
            lon_degrees=waypoint.lon_degrees,
            lon_minutes=waypoint.lon_minutes,
            lon_seconds=waypoint.lon_seconds,
            lon_direction=waypoint.lon_direction,
            magnetic_variation=waypoint.magnetic_variation,
            creator_id=creator_id
        )

        db.add(new_waypoint)
        db.commit()
        db.refresh(new_waypoint)
    except IntegrityError:
        raise common_responses.internal_server_error()

    return new_waypoint.get_clean_waypoint()


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[schemas.WaypointReturn])
async def get_all_waypoints(
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_user)
):
    """
    Get All Waypoints Endpoint.

    Parameters: None

    Returns: 
    - list: list of waypoint dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user["email"], db=db)
    query = text("SELECT waypoint_id FROM aerodromes")
    try:
        aerodrome_ids = [id[0] for id in db.execute(query).fetchall()]
        waypoints = db.query(models.Waypoint).filter(and_(
            ~models.Waypoint.id.in_(aerodrome_ids),
            or_(
                models.Waypoint.creator.has(id=user_id),
                models.Waypoint.is_official == True
            )
        )).all()
    except IntegrityError:
        raise common_responses.internal_server_error()

    return [w.get_clean_waypoint() for w in waypoints]


@router.get("/aerodromes", status_code=status.HTTP_200_OK, response_model=List[schemas.AerodromeReturn])
async def get_all_aerodromes(db: Session = Depends(get_db), current_user: schemas.UserEmail = Depends(auth.validate_user)):
    """
    Get All Aerodromes Endpoint.

    Parameters: None

    Returns: 
    - list: list of aerodrome dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    a = models.Aerodrome
    w = models.Waypoint

    try:
        query_results = db.query(w, a).join(a, w.id == a.waypoint_id).all()
    except IntegrityError:
        raise common_responses.internal_server_error()

    return [{**w.__dict__, **a.__dict__} for w, a in query_results]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.WaypointReturn)
async def post_new_waypoint(
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_user)
):
    """
    Post Waypoint Endpoint.

    Parameters: 
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user["email"], db=db)
    try:
        result = await post_waypoint(waypoint=waypoint, db=db, creator_id=user_id, official=False)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return result


@router.post("/official", status_code=status.HTTP_201_CREATED, response_model=schemas.WaypointReturn)
async def post_official_waypoint(
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_admin_user)
):
    """
    Post Official Waypoint Endpoint.

    Parameters: 
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user["email"], db=db)
    try:
        result = await post_waypoint(waypoint=waypoint, db=db, creator_id=user_id, official=True)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return result


@router.post("/aerodrome", status_code=status.HTTP_201_CREATED, response_model=schemas.AerodromeReturn)
async def post_aerodrome(
    aerodrome: schemas.AerodromeData,
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_admin_user)
):
    """
    Post Aerodrome Endpoint.

    Parameters: 
    - waypoint (dict): the waypoint object to be added.
    - aerodrome (dict): the aerodrome object to be added.

    Returns: 
    - Dic: dictionary with the aerodrome and waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user["email"], db=db)
    try:
        waypoint_result = await post_waypoint(waypoint=aerodrome, db=db, creator_id=user_id, official=True)
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
        raise common_responses.internal_server_error()

    return {**new_aerodrome.__dict__, **waypoint_result.__dict__}
