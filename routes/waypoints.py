"""
FastAPI waypoints router

This module defines the FastAPI waipoints router endpoints.

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

router = APIRouter(tags=["Waypoints"])


async def post_vfr_waypoint(waypoint: schemas.WaypointData, db: Session, creator_id: int):
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

    exists = db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.code == waypoint.code).first()
    if exists:
        is_aerodrome = db.query(models.Aerodrome).filter_by(
            vfr_waypoint_id=exists.waypoint_id).first()

        msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} with code {waypoint.code} already exists. Try using a different code."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    new_waypoint = models.Waypoint(
        lat_degrees=waypoint.lat_degrees,
        lat_minutes=waypoint.lat_minutes,
        lat_seconds=waypoint.lat_seconds,
        lat_direction=waypoint.lat_direction,
        lon_degrees=waypoint.lon_degrees,
        lon_minutes=waypoint.lon_minutes,
        lon_seconds=waypoint.lon_seconds,
        lon_direction=waypoint.lon_direction,
        magnetic_variation=waypoint.magnetic_variation,
    )

    db.add(new_waypoint)
    db.commit()
    db.refresh(new_waypoint)

    new_vfr_waypoint = models.VfrWaypoint(
        waypoint_id=new_waypoint.id,
        code=waypoint.code,
        name=waypoint.name,
        creator_id=creator_id
    )

    db.add(new_vfr_waypoint)
    db.commit()
    new_vfr_waypoint = db.query(models.VfrWaypoint).filter_by(
        waypoint_id=new_waypoint.id).first()
    resp = {**new_vfr_waypoint.__dict__, **new_waypoint.__dict__}
    return resp


async def update_vfr_waypoint(waypoint: schemas.WaypointData, db: Session, creator_id: int, id: int):
    """
    This function updates the waypoint in the database, after performing the necessary checks.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint data.
    - db (sqlalchemy Session): database session.
    - creator_id (int): id of the user.
    - officia (bool): true if the waypoint is official.
    - id (int): waypoint id.

    Returns: 
    Session: Sqlalchemy session qith changes to be commited.

    Raise:
    - HTTPException (400): if waypoint code already exists.
    - HTTPException (500): if there is a server error. 
    """

    exists = db.query(models.VfrWaypoint).filter(and_(
        models.VfrWaypoint.code == waypoint.code,
        not_(models.VfrWaypoint.waypoint_id == id)
    )).first()

    if exists:
        is_aerodrome = db.query(models.Aerodrome).filter_by(
            vfr_waypoint_id=exists.id).first()

        msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} with code {waypoint.code} already exists. Try using a different code."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    waypoint_query = db.query(models.Waypoint).filter(models.Waypoint.id == id)

    if not waypoint_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The waypoint you're trying to update is not in the database."
        )

    waypoint_query.update({
        "lat_degrees": waypoint.lat_degrees,
        "lat_minutes": waypoint.lat_minutes,
        "lat_seconds": waypoint.lat_seconds,
        "lat_direction": waypoint.lat_direction,
        "lon_degrees": waypoint.lon_degrees,
        "lon_minutes": waypoint.lon_minutes,
        "lon_seconds": waypoint.lon_seconds,
        "lon_direction": waypoint.lon_direction,
        "magnetic_variation": waypoint.magnetic_variation
    })

    db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.waypoint_id == id).update({
            "code": waypoint.code,
            "name": waypoint.name,
            "creator_id": creator_id
        })

    return db


@router.get("/vfr", status_code=status.HTTP_200_OK, response_model=List[schemas.WaypointReturn])
async def get_all_vfr_waypoints(
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All VFR Waypoints Endpoint.

    Parameters: None

    Returns: 
    - list: list of waypoint dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    v = models.VfrWaypoint
    w = models.Waypoint

    query_results = db.query(w, v).join(v, w.id == v.waypoint_id).all()

    return [{**w.__dict__, **v.__dict__} for w, v in query_results]


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

    s = models.AerodromeStatus
    a = models.Aerodrome
    v = models.VfrWaypoint
    w = models.Waypoint

    query_results = db.query(w, v, a, s.status)\
        .join(v, w.id == v.waypoint_id)\
        .join(a, v.waypoint_id == a.vfr_waypoint_id)\
        .join(s, a.status_id == s.id).all()

    return [{**w.__dict__, **v.__dict__, **a.__dict__, "status": s} for w, v, a, s in query_results]


@router.post("/vfr", status_code=status.HTTP_201_CREATED, response_model=schemas.WaypointReturn)
async def post_new_vfr_waypoint(
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post VFR Waypoint Endpoint.

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
    result = await post_vfr_waypoint(waypoint=waypoint, db=db, creator_id=user_id)

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

    status_exists = db.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)

    waypoint_result = await post_vfr_waypoint(waypoint=aerodrome, db=db, creator_id=user_id)

    new_aerodrome = models.Aerodrome(
        vfr_waypoint_id=waypoint_result["id"],
        has_taf=aerodrome.has_taf,
        has_metar=aerodrome.has_metar,
        has_fds=aerodrome.has_fds,
        elevation_ft=aerodrome.elevation_ft,
        status_id=aerodrome.status
    )

    db.add(new_aerodrome)
    db.commit()

    a = models.Aerodrome
    s = models.AerodromeStatus
    new_aerodrome = db.query(a, s.status).join(a, a.status_id == s.id).filter(
        a.vfr_waypoint_id == waypoint_result["id"]).first()

    return {**new_aerodrome[0].__dict__, "status": new_aerodrome[1], **waypoint_result}


@router.put("/vfr/{id}", status_code=status.HTTP_200_OK, response_model=schemas.WaypointReturn)
async def edit_vfr_waypoint(
    id,
    waypoint: schemas.WaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit VFR Waypoint Endpoint.

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
    is_aerodrome = db.query(models.Aerodrome).filter(
        models.Aerodrome.vfr_waypoint_id == id).first()
    if is_aerodrome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You're trying to update and aerodrome, please use the apropriate API-endpoint."
        )
    db = await update_vfr_waypoint(waypoint=waypoint, db=db, creator_id=user_id, id=id)

    db.commit()

    w = models.Waypoint
    v = models.VfrWaypoint

    new_waypoint = db.query(w, v).join(
        w, v.waypoint_id == w.id).filter(v.waypoint_id == id).first()
    return {**new_waypoint[0].__dict__, **new_waypoint[1].__dict__}


@router.put("/aerodrome/{id}", status_code=status.HTTP_200_OK, response_model=schemas.AerodromeReturn)
async def edit_aerodrome(
    id,
    aerodrome: schemas.AerodromeData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Aerodrome Endpoint.

    Parameters: 
    - id (int): aerodrome id
    - aerodrome (dict): the aerodrome object to be added.

    Returns: 
    Dic: dictionary with the aerodrome data.

    Raise:
    - HTTPException (400): if aerodrome already exists.
    - HTTPException (500): if there is a server error. 
    """

    aerodrome_query = db.query(models.Aerodrome).filter(
        models.Aerodrome.vfr_waypoint_id == id
    )
    if not aerodrome_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID, the waypoint ID you provided is not an aerodrome."
        )

    status_exists = db.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
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
    db = await update_vfr_waypoint(
        waypoint=waypoint_data,
        db=db,
        creator_id=user_id,
        id=id
    )

    aerodrome_data = {
        "has_taf": aerodrome.has_taf,
        "has_metar": aerodrome.has_metar,
        "has_fds": aerodrome.has_fds,
        "elevation_ft": aerodrome.elevation_ft
    }

    db.query(models.Aerodrome).filter(
        models.Aerodrome.vfr_waypoint_id == id
    ).update({**aerodrome_data, "status_id": aerodrome.status})
    db.commit()

    s = models.AerodromeStatus
    a = models.Aerodrome
    v = models.VfrWaypoint
    w = models.Waypoint

    data = db.query(w, v, a, s.status)\
        .join(v, w.id == v.waypoint_id)\
        .join(a, v.waypoint_id == a.vfr_waypoint_id)\
        .join(s, a.status_id == s.id)\
        .filter(w.id == id).first()

    return {**data[0].__dict__, **data[1].__dict__, **data[2].__dict__, "status": data[3]}


@router.delete("/official/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vfr_waypoint_or_aerodrome(
    id,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete VFR Waypoint or Aerodrome.

    Parameters: 
    id (int): waypoint id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): passenger profile not found.
    - HTTPException (500): if there is a server error. 
    """

    waypoint_query = db.query(models.Waypoint).filter(
        models.Waypoint.id == id)

    not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"The VFR waypoint you're trying to delete is not in the database."
    )
    if not waypoint_query.first():
        raise not_found_exception

    is_vfr_waypoint = db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.waypoint_id == id).first()
    if not is_vfr_waypoint:
        raise not_found_exception

    deleted = waypoint_query.delete(synchronize_session=False)

    if not deleted:
        raise common_responses.internal_server_error()

    db.commit()
