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
    - waypoint (waypoint pydantic schema): waypoint data.
    - db (sqlalchemy Session): database session.
    - creator_id (int): id of the user.
    - officia (bool): true if the waypoint is official.

    Returns: 
    dict: Object with the added waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    db_waypoint_code = f"{waypoint.code}{'' if official else f'@{creator_id}'}"

    try:
        exists = db.query(models.Waypoint).filter(
            models.Waypoint.code == db_waypoint_code).first()
        if exists:
            is_aerodrome = db.query(models.Aerodrome).filter_by(
                waypoint_id=exists.id).first()

            msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} with code {waypoint.code} already exists. Try using a different code."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg
            )

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


async def update_waypoint(waypoint: schemas.WaypointData, db: Session, creator_id: int, official: bool, id: int):
    """
    This function updates the waypoint in the database, after performing the necessary checks.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint data.
    - db (sqlalchemy Session): database session.
    - creator_id (int): id of the user.
    - officia (bool): true if the waypoint is official.
    - id (int): waypoint id.

    Returns: 
    dict: Object with the updated waypoint data.

    Raise:
    - HTTPException (400): if waypoint code already exists.
    - HTTPException (500): if there is a server error. 
    """

    db_waypoint_code = f"{waypoint.code}{'' if official else f'@{creator_id}'}"

    try:
        exists = db.query(models.Waypoint).filter(and_(
            models.Waypoint.code == db_waypoint_code,
            not_(models.Waypoint.id == id)
        )).first()

        if exists:
            is_aerodrome = db.query(models.Aerodrome).filter_by(
                waypoint_id=exists.id).first()

            msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} with code {waypoint.code} already exists. Try using a different code."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg
            )

        waypoint_query = db.query(models.Waypoint).filter(and_(
            models.Waypoint.id == id,
            or_(
                models.Waypoint.creator_id == creator_id,
                official
            )
        ))

        if not waypoint_query.first():
            raise common_responses.invalid_credentials(
                ", or make sure you have permission to perform this operation"
            )

        if not waypoint_query.first().is_official == official:
            official_text = 'official' if not official else 'unofficial'
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This waypoint is {official_text}, please use the {official_text}-waypoint API endpoint."
            )

        waypoint.code = db_waypoint_code
        waypoint_query.update(waypoint.model_dump())
        db.commit()
        new_waypoint = db.query(models.Waypoint).filter(
            models.Waypoint.id == id).first()
    except IntegrityError:
        raise common_responses.internal_server_error()

    return new_waypoint.get_clean_waypoint()


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[schemas.WaypointReturn])
async def get_all_waypoints(
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Waypoints Endpoint.

    Parameters: None

    Returns: 
    - list: list of waypoint dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
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
async def get_all_aerodromes(db: Session = Depends(get_db), current_user: schemas.TokenData = Depends(auth.validate_user)):
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


@router.post("/unofficial", status_code=status.HTTP_201_CREATED, response_model=schemas.WaypointReturn)
async def post_unofficial_waypoint(
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
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

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
    try:
        result = await post_waypoint(waypoint=waypoint, db=db, creator_id=user_id, official=False)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return result


@router.post("/official", status_code=status.HTTP_201_CREATED, response_model=schemas.WaypointReturn)
async def post_official_waypoint(
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
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

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
    try:
        result = await post_waypoint(waypoint=waypoint, db=db, creator_id=user_id, official=True)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return result


@router.post("/aerodrome", status_code=status.HTTP_201_CREATED, response_model=schemas.AerodromeReturn)
async def post_aerodrome(
    aerodrome: schemas.AerodromeData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
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

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
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


@router.put("/unofficial/{id}", status_code=status.HTTP_200_OK, response_model=schemas.WaypointReturn)
async def update_unofficial_waypoint(
    id,
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Update Waypoint Endpoint.

    Parameters: 
    - id (int): waypoint id
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
    try:
        result = await update_waypoint(waypoint=waypoint, db=db, creator_id=user_id, official=False, id=id)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return result


@router.put("/official/{id}", status_code=status.HTTP_200_OK, response_model=schemas.WaypointReturn)
async def update_official_waypoint(
    id,
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Update Official Waypoint Endpoint.

    Parameters: 
    - id (int): waypoint id
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
    try:
        is_aerodrome = db.query(models.Aerodrome).filter(
            models.Aerodrome.waypoint_id == id).first()
        if is_aerodrome:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You're trying to update and aerodrome, please go to the apropriate endpoint."
            )
        result = await update_waypoint(waypoint=waypoint, db=db, creator_id=user_id, official=True, id=id)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return result


@router.put("/aerodrome/{id}", status_code=status.HTTP_200_OK, response_model=schemas.AerodromeReturn)
async def update_aerodrome(
    id,
    aerodrome: schemas.AerodromeData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Update Aerodrome Endpoint.

    Parameters: 
    - id (int): aerodrome id
    - aerodrome (dict): the aerodrome object to be added.

    Returns: 
    Dic: dictionary with the aerodrome data.

    Raise:
    - HTTPException (400): if aerodrome already exists.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
    try:
        aerodrome_query = db.query(models.Aerodrome).filter(
            models.Aerodrome.waypoint_id == id
        )
        if aerodrome_query.first():
            HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID, please provide a valid aerodrome ID."
            )

        waypoint_data = schemas.WaypointData(
            code=aerodrome.code,
            name=aerodrome.name,
            lat_degrees=aerodrome.lat_degrees,
            lat_minutes=aerodrome.lat_minutes,
            lat_seconds=aerodrome.lat_seconds,
            lat_direction=aerodrome.lat_direction,
            lon_degrees=aerodrome.lon_degrees,
            lon_minutes=aerodrome.lon_minutes,
            lon_seconds=aerodrome.lon_seconds,
            lon_direction=aerodrome.lon_direction,
            magnetic_variation=aerodrome.magnetic_variation
        )
        waypoint_result = await update_waypoint(
            waypoint=waypoint_data,
            db=db,
            creator_id=user_id,
            official=True,
            id=id
        )

        aerodrome_data = schemas.AerodromeBase(
            has_taf=aerodrome.has_taf,
            has_metar=aerodrome.has_metar,
            has_fds=aerodrome.has_fds,
            elevation_ft=aerodrome.elevation_ft
        )

        aerodrome_query.update(aerodrome_data.model_dump())
        db.commit()
        new_aerodrome = db.query(models.Aerodrome).filter(
            models.Aerodrome.waypoint_id == id).first()
        new_waypoint = db.query(models.Waypoint).filter(
            models.Waypoint.id == id).first().get_clean_waypoint()

    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return {**new_aerodrome.__dict__, **new_waypoint.__dict__}


@router.delete("/unofficial/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unofficial_waypoint(
    id,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Unofficial Waypoint.

    Parameters: 
    id (int): waypoint id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): passenger profile not found.
    - HTTPException (500): if there is a server error. 
    """

    try:
        user_id = await user_queries.get_id_from(email=current_user.email, db=db)
        waypoint_query = db.query(models.Waypoint).filter(
            models.Waypoint.id == id)

        if not waypoint_query.first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"The waypoint you're trying to delete is not in the database."
            )

        if waypoint_query.first().is_official:
            if not current_user.is_admin:
                raise common_responses.invalid_credentials(
                    " to perform this operation."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request was unsuccessful. If you're trying to delete an official waypoint, please use the 'Delete Official Waypoint' endpoint."
            )

        if not waypoint_query.first().creator_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You do not have valid permissions to delete this waypoint."
            )

        deleted = waypoint_query.delete(synchronize_session=False)

        if not deleted:
            raise common_responses.internal_server_error()

        db.commit()
    except IntegrityError:
        raise common_responses.internal_server_error()


@router.delete("/official/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_official_waypoint_or_aerodrome(
    id,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Official Waypoint or Aerodrome.

    Parameters: 
    id (int): waypoint id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): passenger profile not found.
    - HTTPException (500): if there is a server error. 
    """

    try:
        waypoint_query = db.query(models.Waypoint).filter(
            models.Waypoint.id == id)

        if not waypoint_query.first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"The waypoint you're trying to delete is not in the database."
            )

        user_id = await user_queries.get_id_from(email=current_user.email, db=db)
        if not waypoint_query.first().is_official and\
                not int(waypoint_query.first().creator_id) == user_id:
            raise common_responses.invalid_credentials(
                ", or make sure you have permission to perform this operation"
            )

        deleted = waypoint_query.delete(synchronize_session=False)

        if not deleted:
            raise common_responses.internal_server_error()

        db.commit()
    except IntegrityError:
        raise common_responses.internal_server_error()
