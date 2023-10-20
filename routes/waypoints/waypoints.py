"""
FastAPI user waypoints router

This module defines the FastAPI user waipoints router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
import pytz
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import get_user_id_from_email
from functions.navigation import get_magnetic_variation_for_waypoint

router = APIRouter(tags=["Waypoints"])


@router.get(
    "/user",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.UserWaypointReturn]
)
async def get_all_user_waypoints(
    limit: Optional[int] = -1,
    start: Optional[int] = 0,
    waypoint_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All User Waypoints Endpoint.

    Parameters:
    - limit (int): number of results.
    - start (int): index of the first waypoint.
    - waypoint_id (int): waypoint id.

    Returns: 
    - list: list of waypoint dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """
    u = models.UserWaypoint
    w = models.Waypoint
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

    user_waypoints = db_session.query(w, u)\
        .filter(and_(
            u.creator_id == user_id,
            or_(
                not_(waypoint_id),
                w.id == waypoint_id
            )
        ))\
        .join(u, w.id == u.waypoint_id).order_by(u.name).all()

    limit = len(user_waypoints) if limit == -1 else limit

    return [{
        **w.__dict__,
        **v.__dict__,
        "created_at_utc": pytz.timezone('UTC').localize((v.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((v.last_updated))
    } for w, v in user_waypoints[start: start + limit]]


@router.get(
    "/vfr",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.VfrWaypointReturn]
)
async def get_all_vfr_waypoints(
    limit: Optional[int] = -1,
    start: Optional[int] = 0,
    waypoint_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All VFR Waypoints Endpoint.

    Parameters: 
    - limit (int): number of results.
    - start (int): index of the first waypoint.
    - waypoint_id (int): waypoint id.

    Returns: 
    - list: list of waypoint dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """
    a = models.Aerodrome
    v = models.VfrWaypoint
    w = models.Waypoint

    aerodromes = [item[0] for item in db_session.query(
        a.vfr_waypoint_id).filter(not_(a.vfr_waypoint_id.is_(None))).all()]

    user_is_active_admin = current_user.is_active and current_user.is_admin
    query_results = db_session.query(w, v)\
        .filter(and_(
            or_(
                not_(waypoint_id),
                w.id == waypoint_id
            ),
            not_(w.id.in_(aerodromes)),
            or_(
                not_(v.hidden),
                user_is_active_admin
            )
        ))\
        .join(v, w.id == v.waypoint_id).order_by(v.name).all()

    limit = len(query_results) if limit == -1 else limit
    return [{
        **w.__dict__,
        "code": v.code,
        "name": v.name,
        "hidden": v.hidden if user_is_active_admin else None,
        "created_at_utc": pytz.timezone('UTC').localize((v.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((v.last_updated))
    } for w, v in query_results[start: start + limit]]


@router.get(
    "/aerodromes",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.AerodromeReturnWithRunways]
)
async def get_all_aerodromes(
    limit: Optional[int] = -1,
    start: Optional[int] = 0,
    aerodrome_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Aerodromes Endpoint.

    Parameters: 
    - limit (int): number of results.
    - start (int): index of the first aerodromes.
    - aerodrome_id (optional int): aerodrome id.

    Returns: 
    - list: list of aerodrome dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

    rs = models.RunwaySurface
    s = models.AerodromeStatus
    r = models.Runway
    a = models.Aerodrome
    v = models.VfrWaypoint
    u = models.UserWaypoint
    w = models.Waypoint

    user_is_active_admin = current_user.is_active and current_user.is_admin
    registered_aerodromes = db_session.query(w, v, a, s.status)\
        .filter(and_(
            or_(
                not_(v.hidden),
                user_is_active_admin
            ),
            or_(
                not_(aerodrome_id),
                w.id == aerodrome_id
            )
        ))\
        .join(v, w.id == v.waypoint_id)\
        .join(a, v.waypoint_id == a.vfr_waypoint_id)\
        .join(s, a.status_id == s.id).all()

    private_aerodromes = db_session.query(w, u, a, s.status)\
        .filter(and_(
            or_(
                not_(aerodrome_id),
                w.id == aerodrome_id
            ),
            u.creator_id == user_id
        ))\
        .join(u, w.id == u.waypoint_id)\
        .join(a, u.waypoint_id == a.user_waypoint_id)\
        .join(s, a.status_id == s.id).all()

    aerodromes = registered_aerodromes + private_aerodromes
    aerodrome_ids = [a[2].id for a in aerodromes]

    runways = db_session.query(r, rs.surface)\
        .filter(r.aerodrome_id.in_(aerodrome_ids))\
        .join(rs, r.surface_id == rs.id).all()

    # pylint: disable=cell-var-from-loop
    aerodromes = [{
        **w.__dict__,
        "code": v.code,
        "name": v.name,
        "hidden": v.hidden if a.vfr_waypoint_id is not None and user_is_active_admin else None,
        **a.__dict__,
        "status": s,
        "registered": a.vfr_waypoint_id is not None,
        "created_at_utc": pytz.timezone('UTC').localize((a.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((a.last_updated)),
        "runways": [
            schemas.RunwayInAerodromeReturn(
                id=r.id,
                number=r.number,
                position=r.position,
                length_ft=r.length_ft,
                landing_length_ft=r.landing_length_ft,
                interception_departure_length_ft=r.interception_departure_length_ft,
                surface=rs,
                surface_id=r.surface_id
            ) for r, rs in filter(lambda i: i[0].aerodrome_id == a.id, runways)
        ]
    } for w, v, a, s in aerodromes]

    aerodromes.sort(key=lambda a: (a["registered"], a["name"]))
    limit = len(aerodromes) if limit == -1 else limit
    return aerodromes[start: start + limit]


@router.get(
    "/aerodromes-status",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.AerodromeStatusReturn]
)
async def get_all_aerodrome_status(
    status_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Aerodrome Status Endpoint.

    Parameters: 
    - status_id (optional int): status id.

    Returns: 
    - list: list of aerodrome status dictionaries with status and id.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    return db_session.query(models.AerodromeStatus.id, models.AerodromeStatus.status).filter(or_(
        not_(status_id),
        models.AerodromeStatus.id == status_id
    )).order_by(models.AerodromeStatus.status).all()


@router.post(
    "/user",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.UserWaypointReturn
)
async def post_new_user_waypoint(
    waypoint: schemas.UserWaypointData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post User Waypoint Endpoint.

    Parameters: 
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

    exists = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.creator_id == user_id,
        models.UserWaypoint.code == waypoint.code)
    ).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waypoint with code {waypoint.code} already exists. Try using a different code."
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

    new_user_waypoint = models.UserWaypoint(
        waypoint_id=new_waypoint.id,
        code=waypoint.code,
        name=waypoint.name,
        creator_id=user_id
    )

    db_session.add(new_user_waypoint)
    db_session.commit()
    new_user_waypoint = db_session.query(models.UserWaypoint).filter_by(
        waypoint_id=new_waypoint.id).first()

    return {
        **new_user_waypoint.__dict__,
        **new_waypoint.__dict__,
        "created_at_utc": pytz.timezone('UTC').localize((new_user_waypoint.created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_user_waypoint.last_updated))
    }


@router.post(
    "/private-aerodrome",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PrivateAerodromeReturn
)
async def post_private_aerodrome(
    aerodrome: schemas.PrivateAerodromeData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post Private Aerodrome Endpoint.

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

    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

    waypoint_exists = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.creator_id == user_id,
        models.UserWaypoint.code == aerodrome.code)
    ).first()
    if waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waypoint with code {aerodrome.code} already exists."
        )

    new_waypoint = models.Waypoint(
        lat_degrees=aerodrome.lat_degrees,
        lat_minutes=aerodrome.lat_minutes,
        lat_seconds=aerodrome.lat_seconds,
        lat_direction=aerodrome.lat_direction,
        lon_degrees=aerodrome.lon_degrees,
        lon_minutes=aerodrome.lon_minutes,
        lon_seconds=aerodrome.lon_seconds,
        lon_direction=aerodrome.lon_direction,
        magnetic_variation=aerodrome.magnetic_variation,
    )
    new_waypoint.magnetic_variation = get_magnetic_variation_for_waypoint(
        waypoint=new_waypoint,
        db_session=db_session
    )

    db_session.add(new_waypoint)
    db_session.commit()
    db_session.refresh(new_waypoint)

    new_user_waypoint = models.UserWaypoint(
        waypoint_id=new_waypoint.id,
        code=aerodrome.code,
        name=aerodrome.name,
        creator_id=user_id
    )

    new_aerodrome = models.Aerodrome(
        id=new_waypoint.id,
        user_waypoint_id=new_waypoint.id,
        has_taf=False,
        has_metar=False,
        has_fds=False,
        elevation_ft=aerodrome.elevation_ft,
        status_id=aerodrome.status
    )

    db_session.add(new_user_waypoint)
    db_session.add(new_aerodrome)
    db_session.commit()

    s = models.AerodromeStatus
    a = models.Aerodrome
    u = models.UserWaypoint
    w = models.Waypoint

    return_aerodrome_data = db_session.query(w, u, a, s.status)\
        .filter(w.id == new_waypoint.id)\
        .join(u, w.id == u.waypoint_id)\
        .join(a, u.waypoint_id == a.user_waypoint_id)\
        .join(s, a.status_id == s.id).first()

    return {
        **return_aerodrome_data[0].__dict__,
        **return_aerodrome_data[1].__dict__,
        **return_aerodrome_data[2].__dict__,
        "status": return_aerodrome_data[3],
        "registered": False,
        "created_at_utc": pytz.timezone('UTC').localize((return_aerodrome_data[2].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((return_aerodrome_data[2].last_updated))
    }


@router.put(
    "/user/{waypoint_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.UserWaypointReturn
)
async def edit_user_waypoint(
    waypoint_id: int,
    waypoint: schemas.UserWaypointData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit User Waypoint Endpoint.

    Parameters: 
    - waypoint_id (int): waypoint id
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

    user_waypoint_exists = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == waypoint_id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not user_waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The waypoint you're trying to update is not in the database."
        )

    duplicated_code = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.code == waypoint.code,
        not_(models.UserWaypoint.waypoint_id == waypoint_id)
    )).first()

    if duplicated_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waypoint with code {waypoint.code} already exists."
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

    db_session.query(models.Waypoint).filter(models.Waypoint.id == waypoint_id).update(
        update_waypoint_data
    )

    db_session.query(models.UserWaypoint).filter(
        models.UserWaypoint.waypoint_id == waypoint_id).update({
            "code": waypoint.code,
            "name": waypoint.name,
            "creator_id": user_id
        })

    db_session.commit()

    w = models.Waypoint
    u = models.UserWaypoint

    new_waypoint = db_session.query(w, u).join(
        w, u.waypoint_id == w.id).filter(u.waypoint_id == waypoint_id).first()
    return {
        **new_waypoint[0].__dict__,
        **new_waypoint[1].__dict__,
        "created_at_utc": pytz.timezone('UTC').localize((new_waypoint[1].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((new_waypoint[1].last_updated))
    }


@router.put(
    "/private-aerodrome/{aerodrome_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.PrivateAerodromeReturn
)
async def edit_private_aerodrome(
    aerodrome_id: int,
    aerodrome: schemas.PrivateAerodromeData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Private Aerodrome Endpoint.

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
        models.Aerodrome.user_waypoint_id == aerodrome_id
    )
    if not aerodrome_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID, the waypoint ID you provided is not an aerodrome."
        )

    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    user_waypoint_query = db_session.query(models.UserWaypoint).filter(
        and_(
            models.UserWaypoint.waypoint_id == aerodrome_id,
            models.UserWaypoint.creator_id == user_id
        )
    )
    if not user_waypoint_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID, you do not have permissio to edit this waypoint."
        )

    status_exists = db_session.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    duplicated_code = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.code == aerodrome.code,
        not_(models.UserWaypoint.waypoint_id == aerodrome_id)
    )).first()

    if duplicated_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aerodrome with code {aerodrome.code} already exists."
        )

    update_waypoint_data = {
        "lat_degrees": aerodrome.lat_degrees,
        "lat_minutes": aerodrome.lat_minutes,
        "lat_seconds": aerodrome.lat_seconds,
        "lat_direction": aerodrome.lat_direction,
        "lon_degrees": aerodrome.lon_degrees,
        "lon_minutes": aerodrome.lon_minutes,
        "lon_seconds": aerodrome.lon_seconds,
        "lon_direction": aerodrome.lon_direction,
    }
    if aerodrome.magnetic_variation is not None:
        update_waypoint_data["magnetic_variation"] = aerodrome.magnetic_variation

    db_session.query(models.Waypoint).filter(
        models.Waypoint.id == aerodrome_id).update(update_waypoint_data)

    db_session.query(models.UserWaypoint).filter(
        models.UserWaypoint.waypoint_id == aerodrome_id).update({
            "code": aerodrome.code,
            "name": aerodrome.name,
            "creator_id": user_id
        })

    aerodrome_data = {
        "elevation_ft": aerodrome.elevation_ft
    }

    db_session.query(models.Aerodrome).filter(
        models.Aerodrome.user_waypoint_id == aerodrome_id
    ).update({**aerodrome_data, "status_id": aerodrome.status})

    db_session.commit()

    s = models.AerodromeStatus
    a = models.Aerodrome
    u = models.UserWaypoint
    w = models.Waypoint

    data = db_session.query(w, u, a, s.status)\
        .join(u, w.id == u.waypoint_id)\
        .join(a, u.waypoint_id == a.user_waypoint_id)\
        .join(s, a.status_id == s.id)\
        .filter(w.id == aerodrome_id).first()

    return {
        **data[0].__dict__,
        **data[1].__dict__,
        **data[2].__dict__,
        "status": data[3],
        "registered": False,
        "created_at_utc": pytz.timezone('UTC').localize((data[2].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((data[2].last_updated))
    }


@router.delete("/user/{waypoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_waypoint_or_private_aerodrome(
    waypoint_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete User Waypoint or Private Aerodrome.

    Parameters: 
    waypoint_id (int): waypoint id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): waypoint not found.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    waypoint_exists = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == waypoint_id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The waypoint you're trying to delete is not in the database."
        )

    deleted = db_session.query(models.Waypoint).filter(
        models.Waypoint.id == waypoint_id).delete(synchronize_session=False)

    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()
