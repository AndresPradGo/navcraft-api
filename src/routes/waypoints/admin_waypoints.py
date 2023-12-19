"""
FastAPI vfr waypoints router

This module defines the FastAPI vfr waipoints router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

import re

from fastapi import APIRouter, Depends, status, HTTPException
import pytz
from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import get_user_id_from_email, clean_string
from functions.navigation import get_magnetic_variation_for_waypoint


router = APIRouter(tags=["Admin Waypoints"])


def post_vfr_waypoint(
        waypoint: schemas.VfrWaypointData,
        db_session: Session,
        creator_id: int
):
    """
    This function checks if the waypoint passed as a parameter
    already exists in the database, and adds it to the database, 
    or returns and error response.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint data.
    - creator_id (int): id of the user.

    Returns: 
    dict: Object with the added waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    exists = db_session.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.code == waypoint.code).first()
    if exists:
        is_aerodrome = db_session.query(models.Aerodrome).filter_by(
            vfr_waypoint_id=exists.waypoint_id).first()

        msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} '{waypoint.code}' already exists."
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
    new_waypoint.magnetic_variation = get_magnetic_variation_for_waypoint(
        waypoint=new_waypoint,
        db_session=db_session
    )

    db_session.add(new_waypoint)
    db_session.commit()
    db_session.refresh(new_waypoint)

    new_vfr_waypoint = models.VfrWaypoint(
        waypoint_id=new_waypoint.id,
        code=waypoint.code,
        name=waypoint.name,
        hidden=waypoint.hidden,
        creator_id=creator_id
    )

    db_session.add(new_vfr_waypoint)
    db_session.commit()
    new_vfr_waypoint = db_session.query(models.VfrWaypoint).filter_by(
        waypoint_id=new_waypoint.id).first()

    return {**new_vfr_waypoint.__dict__, **new_waypoint.__dict__}


def update_vfr_waypoint(
        waypoint: schemas.VfrWaypointData,
        db_session: Session,
        creator_id: int,
        waypoint_id: int
):
    """
    This function updates the waypoint in the database, after performing the necessary checks.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint data.
    - creator_id (int): id of the user.
    - waypoint_id (int): waypoint id.

    Returns: 
    Session: Sqlalchemy session qith changes to be commited.

    Raise:
    - HTTPException (400): if waypoint code already exists.
    - HTTPException (500): if there is a server error. 
    """

    vfr_waypoint_exists = db_session.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.waypoint_id == waypoint_id).first()

    if not vfr_waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The waypoint you're trying to update is not in the database."
        )

    duplicated_code = db_session.query(models.VfrWaypoint).filter(and_(
        models.VfrWaypoint.code == waypoint.code,
        not_(models.VfrWaypoint.waypoint_id == waypoint_id)
    )).first()

    if duplicated_code:
        is_aerodrome = db_session.query(models.Aerodrome).filter_by(
            vfr_waypoint_id=vfr_waypoint_exists.waypoint_id).first()

        msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} '{waypoint.code}' already exists."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    update_waypoint_data = {
        "lat_degrees": waypoint.lat_degrees,
        "lat_minutes": waypoint.lat_minutes,
        "lat_seconds": waypoint.lat_seconds,
        "lat_direction": waypoint.lat_direction,
        "lon_degrees": waypoint.lon_degrees,
        "lon_minutes": waypoint.lon_minutes,
        "lon_seconds": waypoint.lon_seconds,
        "lon_direction": waypoint.lon_direction,
    }
    if waypoint.magnetic_variation is not None:
        update_waypoint_data["magnetic_variation"] = waypoint.magnetic_variation

    db_session.query(models.Waypoint).filter(
        models.Waypoint.id == waypoint_id).update(update_waypoint_data)

    db_session.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.waypoint_id == waypoint_id).update({
            "code": waypoint.code,
            "name": waypoint.name,
            "creator_id": creator_id,
            "hidden": waypoint.hidden
        })

    return db_session


@router.post(
    "/vfr",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.VfrWaypointReturn
)
def post_new_vfr_waypoint(
    waypoint: schemas.VfrWaypointData,
    db_session: Session = Depends(get_db),
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

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    result = post_vfr_waypoint(
        waypoint=waypoint, db_session=db_session, creator_id=user_id)

    return {
        **result,
        "created_at_utc": pytz.timezone('UTC').localize((result["created_at"])),
        "last_updated_utc": pytz.timezone('UTC').localize((result["last_updated"]))
    }


@router.post(
    "/registered-aerodrome",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.RegisteredAerodromeReturn
)
def post_registered_aerodrome(
    aerodrome: schemas.RegisteredAerodromeData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Registered Aerodrome Endpoint.

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

    status_exists = db_session.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)

    waypoint_result = post_vfr_waypoint(
        waypoint=aerodrome,
        db_session=db_session,
        creator_id=user_id
    )

    new_aerodrome = models.Aerodrome(
        id=waypoint_result["id"],
        vfr_waypoint_id=waypoint_result["id"],
        has_taf=aerodrome.has_taf,
        has_metar=aerodrome.has_metar,
        has_fds=aerodrome.has_fds,
        elevation_ft=aerodrome.elevation_ft,
        status_id=aerodrome.status
    )

    db_session.add(new_aerodrome)
    db_session.commit()

    a = models.Aerodrome
    s = models.AerodromeStatus
    new_aerodrome = db_session.query(a, s.status).join(a, a.status_id == s.id).filter(
        a.vfr_waypoint_id == waypoint_result["id"]).first()

    return {
        **new_aerodrome[0].__dict__,
        "status": new_aerodrome[1],
        **waypoint_result,
        "registered": True,
        "created_at_utc": pytz.timezone('UTC').localize((new_aerodrome[0].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_aerodrome[0].last_updated))
    }


@router.post(
    "/aerodrome-status",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AerodromeStatusReturn
)
def post_aerodrome_status(
    aerodrome_status: str,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Aerodrome Status Endpoint.

    Parameters: 
    - status (dict): the aerodrom status to be added.

    Returns: 
    - Dic: dictionary with the aerodrome status and id.

    Raise:
    - HTTPException (400): if aerodrome status already exists, or it
      contains characters other than letters, hyphen and white space.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    pattern = r'^[-A-Za-z ]*$'
    status_matches_pattern = re.match(pattern, aerodrome_status) is not None
    if not status_matches_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use only letters, hyphens, and spaces in the aerodrome status."
        )

    clean_status = clean_string(aerodrome_status)

    already_exists = db_session.query(models.AerodromeStatus).filter_by(
        status=clean_status).first()
    if already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aerodrome status already exists."
        )

    new_aerodrome_status = models.AerodromeStatus(status=clean_status)
    db_session.add(new_aerodrome_status)
    db_session.commit()
    db_session.refresh(new_aerodrome_status)

    return new_aerodrome_status


@router.put(
    "/vfr/{waypoint_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.VfrWaypointReturn
)
def edit_vfr_waypoint(
    waypoint_id: int,
    waypoint: schemas.VfrWaypointData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit VFR Waypoint Endpoint.

    Parameters: 
    - waypoint_id (int): waypoint id
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    is_aerodrome = db_session.query(models.Aerodrome).filter(
        models.Aerodrome.vfr_waypoint_id == waypoint_id).first()
    if is_aerodrome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You're trying to update and aerodrome, please use the apropriate API-endpoint."
        )
    db_session = update_vfr_waypoint(
        waypoint=waypoint,
        db_session=db_session,
        creator_id=user_id,
        waypoint_id=waypoint_id
    )

    db_session.commit()

    w = models.Waypoint
    v = models.VfrWaypoint

    new_waypoint = db_session.query(w, v).join(
        w, v.waypoint_id == w.id).filter(v.waypoint_id == waypoint_id).first()
    return {
        **new_waypoint[0].__dict__,
        **new_waypoint[1].__dict__,
        "created_at_utc": pytz.timezone('UTC').localize((new_waypoint[0].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_waypoint[0].last_updated))}


@router.put(
    "/registered-aerodrome/{aerodrome_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RegisteredAerodromeReturn
)
def edit_registered_aerodrome(
    aerodrome_id: int,
    aerodrome: schemas.RegisteredAerodromeData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Registered Aerodrome Endpoint.

    Parameters: 
    - aerodrome_id (int): aerodrome id
    - aerodrome (dict): the aerodrome object to be added.

    Returns: 
    Dic: dictionary with the aerodrome data.

    Raise:
    - HTTPException (400): if aerodrome already exists.
    - HTTPException (500): if there is a server error. 
    """

    aerodrome_query = db_session.query(models.Aerodrome).filter(
        models.Aerodrome.vfr_waypoint_id == aerodrome_id
    )
    if not aerodrome_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID, the waypoint ID you provided is not an aerodrome."
        )

    status_exists = db_session.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    waypoint_data = schemas.VfrWaypointData(
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
        magnetic_variation=aerodrome.magnetic_variation,
        hidden=aerodrome.hidden
    )
    db_session = update_vfr_waypoint(
        waypoint=waypoint_data,
        db_session=db_session,
        creator_id=user_id,
        waypoint_id=aerodrome_id
    )

    aerodrome_data = {
        "has_taf": aerodrome.has_taf,
        "has_metar": aerodrome.has_metar,
        "has_fds": aerodrome.has_fds,
        "elevation_ft": aerodrome.elevation_ft
    }

    db_session.query(models.Aerodrome).filter(
        models.Aerodrome.vfr_waypoint_id == aerodrome_id
    ).update({**aerodrome_data, "status_id": aerodrome.status})
    db_session.commit()

    s = models.AerodromeStatus
    a = models.Aerodrome
    v = models.VfrWaypoint
    w = models.Waypoint

    data = db_session.query(w, v, a, s.status)\
        .join(v, w.id == v.waypoint_id)\
        .join(a, v.waypoint_id == a.vfr_waypoint_id)\
        .join(s, a.status_id == s.id)\
        .filter(w.id == aerodrome_id).first()

    return {
        **data[0].__dict__,
        **data[1].__dict__,
        **data[2].__dict__,
        "status": data[3],
        "registered": True,
        "created_at_utc": pytz.timezone('UTC').localize((data[0].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((data[0].last_updated))
    }


@router.delete("/registered/{waypoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vfr_waypoints_or_aerodromes(
    waypoint_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete VFR Waypoint or Aerodrome.

    Parameters: 
    waypoint_id int: waypoint id to be deleted.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): waypoint not found.
    - HTTPException (500): if there is a server error. 
    """

    waypoint_query = db_session.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.waypoint_id == waypoint_id).first()

    if not waypoint_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The Waypoint or Aerodrome you're trying to delete, is not in the database."
        )

    deleted = db_session.query(models.Waypoint).filter(
        models.Waypoint.id == waypoint_id).delete(synchronize_session=False)

    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()


@router.delete("/aerodrome-status/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aerodrome_status(
    status_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Aerodrome Status.

    Parameters: 
    status_id (int): status id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    status_query = db_session.query(models.AerodromeStatus).filter(
        models.AerodromeStatus.id == status_id)

    if not status_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The aerodrome status you're trying to delete is not in the database."
        )

    deleted = status_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db_session.commit()
