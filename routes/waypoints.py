"""
FastAPI waypoints router

This module defines the FastAPI waipoints router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.functions import get_user_id_from_email

from utils.db import get_db
from utils.functions import clean_string

router = APIRouter(tags=["Waypoints"])


async def post_vfr_waypoint(waypoint: schemas.VfrWaypointData, db: Session, creator_id: int):
    """
    This function checks if the waypoint passed as a parameter
    already exists in the database, and adds it to the database, 
    or returns and error response.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint data.
    - db (sqlalchemy Session): database session.
    - creator_id (int): id of the user.

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
        hidden=waypoint.hidden,
        creator_id=creator_id
    )

    db.add(new_vfr_waypoint)
    db.commit()
    new_vfr_waypoint = db.query(models.VfrWaypoint).filter_by(
        waypoint_id=new_waypoint.id).first()

    return {**new_vfr_waypoint.__dict__, **new_waypoint.__dict__}


async def update_vfr_waypoint(waypoint: schemas.VfrWaypointData, db: Session, creator_id: int, id: int):
    """
    This function updates the waypoint in the database, after performing the necessary checks.

    Parameters: 
    - waypoint (waypoint pydantic schema): waypoint data.
    - db (sqlalchemy Session): database session.
    - creator_id (int): id of the user.
    - id (int): waypoint id.

    Returns: 
    Session: Sqlalchemy session qith changes to be commited.

    Raise:
    - HTTPException (400): if waypoint code already exists.
    - HTTPException (500): if there is a server error. 
    """

    vfr_waypoint_exists = db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.waypoint_id == id).first()

    if not vfr_waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The waypoint you're trying to update is not in the database."
        )

    duplicated_code = db.query(models.VfrWaypoint).filter(and_(
        models.VfrWaypoint.code == waypoint.code,
        not_(models.VfrWaypoint.waypoint_id == id)
    )).first()

    if duplicated_code:
        is_aerodrome = db.query(models.Aerodrome).filter_by(
            vfr_waypoint_id=vfr_waypoint_exists.waypoint_id).first()

        msg = f"{'Aerodrome' if is_aerodrome else 'Waypoint'} with code {waypoint.code} already exists. Try using a different code."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    db.query(models.Waypoint).filter(
        models.Waypoint.id == id).update({
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
            "creator_id": creator_id,
            "hidden": waypoint.hidden
        })

    return db


@router.get("/user", status_code=status.HTTP_200_OK, response_model=List[schemas.UserWaypointReturn])
async def get_all_user_waypoints(
    ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All User Waypoints Endpoint.

    Parameters:
    - ids (optional list[int]): list of waypoint ids.

    Returns: 
    - list: list of waypoint dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """
    u = models.UserWaypoint
    w = models.Waypoint
    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    user_waypoints = db.query(w, u)\
        .filter(and_(
            u.creator_id == user_id,
            or_(
                not_(ids),
                w.id.in_(ids)
            )
        ))\
        .join(u, w.id == u.waypoint_id).all()

    return [{**w.__dict__, **v.__dict__} for w, v in user_waypoints]


@router.get("/vfr/csv", status_code=status.HTTP_200_OK)
async def get_csv_file_with_all_vfr_waypoints(
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Get CSV File With All VFR Waypoints Endpoint.

    Parameters: None

    Returns: 
    - CSV file: csv file with a list of VFR Waypoints.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    a = models.Aerodrome
    v = models.VfrWaypoint
    w = models.Waypoint

    aerodromes = [item[0] for item in db.query(
        a.vfr_waypoint_id).filter(not_(a.vfr_waypoint_id.is_(None))).all()]

    query_results = db.query(w, v)\
        .filter(not_(w.id.in_(aerodromes)))\
        .join(v, w.id == v.waypoint_id).all()

    data = [{
        "code": v.code,
        "name": v.name,
        "lat_degrees": w.lat_degrees,
        "lat_minutes": w.lat_minutes,
        "lat_seconds": w.lat_seconds,
        "lat_direction": w.lat_direction,
        "lon_degrees": w.lon_degrees,
        "lon_minutes": w.lon_minutes,
        "lon_seconds": w.lon_seconds,
        "lon_direction": w.lon_direction,
        "magnetic_variation": w.magnetic_variation,
        "hidden": v.hidden
    } for w, v in query_results]

    buffer = csv.list_to_buffer(data=data)

    response = StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"}
    )
    return response


@router.get("/vfr", status_code=status.HTTP_200_OK, response_model=List[schemas.VfrWaypointReturn])
async def get_all_vfr_waypoints(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All VFR Waypoints Endpoint.

    Parameters: 
    - ids (optional list[int]): list of waypoint ids.

    Returns: 
    - list: list of waypoint dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """
    a = models.Aerodrome
    v = models.VfrWaypoint
    w = models.Waypoint

    aerodromes = [item[0] for item in db.query(
        a.vfr_waypoint_id).filter(not_(a.vfr_waypoint_id.is_(None))).all()]

    user_is_active_admin = current_user.is_active and current_user.is_admin
    query_results = db.query(w, v)\
        .filter(and_(
            or_(
                not_(id),
                w.id == id
            ),
            not_(w.id.in_(aerodromes)),
            or_(
                not_(v.hidden),
                user_is_active_admin
            )
        ))\
        .join(v, w.id == v.waypoint_id).all()

    return [{
        **w.__dict__,
        "code": v.code,
        "name": v.name,
        "hidden": v.hidden if user_is_active_admin else None,
    } for w, v in query_results]


@router.get("/aerodromes/csv", status_code=status.HTTP_200_OK)
async def get_csv_file_with_all_aerodromes(
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Get CSV File With All Aerodromes Endpoint.

    Parameters: None

    Returns: 
    - CSV file: csv file with a list of aerodromes (does not include the runways).

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    a = models.Aerodrome
    v = models.VfrWaypoint
    w = models.Waypoint

    aerodromes = db.query(w, v, a)\
        .filter(not_(a.vfr_waypoint_id.is_(None)))\
        .join(v, w.id == v.waypoint_id)\
        .join(a, v.waypoint_id == a.vfr_waypoint_id).all()

    data = [{
        "code": v.code,
        "name": v.name,
        "lat_degrees": w.lat_degrees,
        "lat_minutes": w.lat_minutes,
        "lat_seconds": w.lat_seconds,
        "lat_direction": w.lat_direction,
        "lon_degrees": w.lon_degrees,
        "lon_minutes": w.lon_minutes,
        "lon_seconds": w.lon_seconds,
        "lon_direction": w.lon_direction,
        "elevation_ft": a.elevation_ft,
        "magnetic_variation": w.magnetic_variation,
        "has_taf": a.has_taf,
        "has_metar": a.has_metar,
        "has_fds": a.has_fds,
        "hidden": v.hidden,
        "status_id": a.status_id
    } for w, v, a in aerodromes]

    buffer = csv.list_to_buffer(data=data)

    response = StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"}
    )
    return response


@router.get("/aerodromes", status_code=status.HTTP_200_OK, response_model=List[schemas.AerodromeReturnWithRunways])
async def get_all_aerodromes(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Aerodromes Endpoint.

    Parameters: 
    - id (optional int): aerodrome id.

    Returns: 
    - list: list of aerodrome dictionaries.

    Raise:
    - HTTPException (500): if there is a server error. 
    """
    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    rs = models.RunwaySurface
    s = models.AerodromeStatus
    r = models.Runway
    a = models.Aerodrome
    v = models.VfrWaypoint
    u = models.UserWaypoint
    w = models.Waypoint

    user_is_active_admin = current_user.is_active and current_user.is_admin
    registered_aerodromes = db.query(w, v, a, s.status)\
        .filter(and_(
            or_(
                not_(v.hidden),
                user_is_active_admin
            ),
            or_(
                not_(id),
                w.id == id
            )
        ))\
        .join(v, w.id == v.waypoint_id)\
        .join(a, v.waypoint_id == a.vfr_waypoint_id)\
        .join(s, a.status_id == s.id).all()

    private_aerodromes = db.query(w, u, a, s.status)\
        .filter(and_(
            or_(
                not_(id),
                w.id == id
            ),
            u.creator_id == user_id
        ))\
        .join(u, w.id == u.waypoint_id)\
        .join(a, u.waypoint_id == a.user_waypoint_id)\
        .join(s, a.status_id == s.id).all()

    aerodromes = registered_aerodromes + private_aerodromes
    aerodrome_ids = [a[2].id for a in aerodromes]

    runways = db.query(r, rs.surface)\
        .filter(r.aerodrome_id.in_(aerodrome_ids))\
        .join(rs, r.surface_id == rs.id).all()

    return [{
            **w.__dict__,
            "code": v.code,
            "name": v.name,
            "hidden": v.hidden if user_is_active_admin else None,
            **a.__dict__,
            "status": s,
            "registered": a.vfr_waypoint_id is not None,
            "runways": [
                schemas.RunwayInAerodromeReturn(
                    id=r.id,
                    number=r.number,
                    position=r.position,
                    length_ft=r.length_ft,
                    surface=rs,
                    surface_id=r.surface_id
                ) for r, rs in filter(lambda i: i[0].aerodrome_id == a.id, runways)
            ]
            } for w, v, a, s in aerodromes]


@router.get("/aerodromes-status", status_code=status.HTTP_200_OK, response_model=List[schemas.AerodromeStatusReturn])
async def get_all_aerodrome_status(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Aerodrome Status Endpoint.

    Parameters: 
    - id (optional int): waypoint id.

    Returns: 
    - list: list of aerodrome status dictionaries with status and id.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    return db.query(models.AerodromeStatus.id, models.AerodromeStatus.status).filter(or_(
        not_(id),
        models.AerodromeStatus.id == id
    )).all()


@router.post("/vfr/csv", status_code=status.HTTP_204_NO_CONTENT)
async def manage_vfr_waypoints_with_csv_file(
    csv_file: UploadFile,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Manage VFR Waypoints Endpoint.

    Usage:
    - Download the VFR-Waypoint csv-list, from the "Get Csv File With All Vfr Waypoints" endpoint.
    - Use this file to update the list in the desired way.
    - New columns can be added for your reference, but they won't be considered for updating the 
      data in the database. 
    - Do not delete or edit the headers of the existing colums in any way, or the file will be rejected.
    - Enter all data in the correct colum to ensure data integrity.
    - Make sure there are no typos or repeated entries.
    - After getting a 204 response, download csv list again to check it has been uploaded correctly.

    NOTE: This endpoint will post new data-entries, and updata existing ones, but it will not delete any 
    entries already in the database. To delete existing data-entries, use the appropriate delete endpoint.

    Parameters: 
    - csv-file (UploadFile): csv file with VFR Waypoint data.

    Returns: None

    Raise:
    - HTTPException (400): file or file-data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Check and decode csv-file
    csv.check_format(csv_file)

    # Get list of schemas
    data_list = await csv.extract_schemas(file=csv_file, schema=schemas.VfrWaypointData)

    # Check there are no repeated codes
    codes_set = {v.code for v in data_list}
    if not len(data_list) == len(set(codes_set)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There are repeated waypoint-codes in your list, please make sure all waypoints are unique."
        )

    # Find waypoints already in database
    db_vfr_waypoints = db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.code.in_(codes_set)).all()
    db_vfr_waypoint_ids = {v.code: v.waypoint_id for v in db_vfr_waypoints}

    # Divide list into data to add and data to edit
    data_to_add = [v for v in filter(
        lambda i: not i.code in list(db_vfr_waypoint_ids.keys()), data_list)]
    data_to_edit = [v for v in filter(
        lambda i: i.code in list(db_vfr_waypoint_ids.keys()), data_list)]

    # Add data
    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    for waypoint in data_to_add:
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
            hidden=waypoint.hidden,
            creator_id=user_id
        )
        db.add(new_vfr_waypoint)
        db.commit()

    # Edit data
    for waypoint in data_to_edit:
        waypoint_to_edit = {
            "id": db_vfr_waypoint_ids[waypoint.code],
            "lat_degrees": waypoint.lat_degrees,
            "lat_minutes": waypoint.lat_minutes,
            "lat_seconds": waypoint.lat_seconds,
            "lat_direction": waypoint.lat_direction,
            "lon_degrees": waypoint.lon_degrees,
            "lon_minutes": waypoint.lon_minutes,
            "lon_seconds": waypoint.lon_seconds,
            "lon_direction": waypoint.lon_direction,
            "magnetic_variation": waypoint.magnetic_variation
        }
        db.query(models.Waypoint)\
            .filter(models.Waypoint.id == waypoint_to_edit["id"])\
            .update(waypoint_to_edit, synchronize_session=False)

        vfr_waypoint_to_edit = {
            "waypoint_id": db_vfr_waypoint_ids[waypoint.code],
            "code": waypoint.code,
            "name": waypoint.name,
            "creator_id": user_id,
            "hidden": waypoint.hidden
        }
        db.query(models.VfrWaypoint)\
            .filter(models.VfrWaypoint.waypoint_id == vfr_waypoint_to_edit["waypoint_id"])\
            .update(vfr_waypoint_to_edit, synchronize_session=False)

    db.commit()


@router.post("/vfr", status_code=status.HTTP_201_CREATED, response_model=schemas.VfrWaypointReturn)
async def post_new_vfr_waypoint(
    waypoint: schemas.VfrWaypointData,
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

    user_id = await get_user_id_from_email(email=current_user.email, db=db)
    result = await post_vfr_waypoint(waypoint=waypoint, db=db, creator_id=user_id)

    return result


@router.post("/user", status_code=status.HTTP_201_CREATED, response_model=schemas.UserWaypointReturn)
async def post_new_user_waypoint(
    waypoint: schemas.UserWaypointData,
    db: Session = Depends(get_db),
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

    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    exists = db.query(models.UserWaypoint).filter(and_(
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

    db.add(new_waypoint)
    db.commit()
    db.refresh(new_waypoint)

    new_user_waypoint = models.UserWaypoint(
        waypoint_id=new_waypoint.id,
        code=waypoint.code,
        name=waypoint.name,
        creator_id=user_id
    )

    db.add(new_user_waypoint)
    db.commit()
    new_user_waypoint = db.query(models.UserWaypoint).filter_by(
        waypoint_id=new_waypoint.id).first()

    return {**new_user_waypoint.__dict__, **new_waypoint.__dict__}


@router.post("/private-aerodrome", status_code=status.HTTP_201_CREATED, response_model=schemas.PrivateAerodromeReturn)
async def post_private_aerodrome(
    aerodrome: schemas.PrivateAerodromeData,
    db: Session = Depends(get_db),
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

    status_exists = db.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    waypoint_exists = db.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.creator_id == user_id,
        models.UserWaypoint.code == aerodrome.code)
    ).first()
    if waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waypoint with code {aerodrome.code} already exists. Try using a different code."
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

    db.add(new_waypoint)
    db.commit()
    db.refresh(new_waypoint)

    new_user_waypoint = models.UserWaypoint(
        waypoint_id=new_waypoint.id,
        code=aerodrome.code,
        name=aerodrome.name,
        creator_id=user_id
    )

    new_aerodrome = models.Aerodrome(
        id=new_waypoint.id,
        user_waypoint_id=new_waypoint.id,
        has_taf=aerodrome.has_taf,
        has_metar=aerodrome.has_metar,
        has_fds=aerodrome.has_fds,
        elevation_ft=aerodrome.elevation_ft,
        status_id=aerodrome.status
    )

    db.add(new_user_waypoint)
    db.add(new_aerodrome)
    db.commit()

    s = models.AerodromeStatus
    a = models.Aerodrome
    u = models.UserWaypoint
    w = models.Waypoint

    r = db.query(w, u, a, s.status)\
        .filter(w.id == new_waypoint.id)\
        .join(u, w.id == u.waypoint_id)\
        .join(a, u.waypoint_id == a.user_waypoint_id)\
        .join(s, a.status_id == s.id).first()

    return {**r[0].__dict__, **r[1].__dict__, **r[2].__dict__, "status": r[3], "registered": False}


@router.post("/registered-aerodrome/csv", status_code=status.HTTP_204_NO_CONTENT)
async def manage_registered_aerodrome_with_csv_file(
    csv_file: UploadFile,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Manage Registered Aerodrome Endpoint.

    Usage:
    - Download the Registered-Aerodrome csv-list, from the "Get Csv File With All Aerodrome" endpoint.
    - Use this file to update the list in the desired way.
    - New columns can be added for your reference, but they won't be considered for updating the 
      data in the database. 
    - Do not delete or edit the headers of the existing colums in any way, or the file will be rejected.
    - Enter all data in the correct colum to ensure data integrity.
    - Make sure there are no typos or repeated entries.
    - After getting a 204 response, download csv list again to check it has been uploaded correctly.

    NOTE: This endpoint will post new data-entries, and updata existing ones, but it will not delete any 
    entries already in the database. To delete existing data-entries, use the appropriate delete endpoint.

    Parameters: 
    - csv-file (UploadFile): csv file with registered aerodrome data.

    Returns: None

    Raise:
    - HTTPException (400): file or file-data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check and decode csv-file
    csv.check_format(csv_file)

    # Get list of schemas
    data_list = await csv.extract_schemas(file=csv_file, schema=schemas.RegisteredAerodromeData)

    # Check there are no repeated codes
    codes_set = {v.code for v in data_list}
    if not len(data_list) == len(set(codes_set)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There are repeated aerodrome-codes in your list, please make sure all aerodromes are unique."
        )

    # Find waypoints already in database
    db_vfr_waypoints = db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.code.in_(codes_set)).all()
    db_vfr_waypoint_ids = {v.code: v.waypoint_id for v in db_vfr_waypoints}

    # Divide list into data to add and data to edit
    data_to_add = [v for v in filter(
        lambda i: not i.code in list(db_vfr_waypoint_ids.keys()), data_list)]
    data_to_edit = [v for v in filter(
        lambda i: i.code in list(db_vfr_waypoint_ids.keys()), data_list)]

    # Add data
    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    for aerodrome in data_to_add:
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
        db.add(new_waypoint)
        db.commit()
        db.refresh(new_waypoint)

        new_vfr_waypoint = models.VfrWaypoint(
            waypoint_id=new_waypoint.id,
            code=aerodrome.code,
            name=aerodrome.name,
            hidden=aerodrome.hidden,
            creator_id=user_id
        )
        db.add(new_vfr_waypoint)

        new_aerodrome = models.Aerodrome(
            id=new_waypoint.id,
            vfr_waypoint_id=new_waypoint.id,
            has_taf=aerodrome.has_taf,
            has_metar=aerodrome.has_metar,
            has_fds=aerodrome.has_fds,
            elevation_ft=aerodrome.elevation_ft,
            status_id=aerodrome.status
        )
        db.add(new_aerodrome)
        db.commit()

    # Edit data
    for aerodrome in data_to_edit:
        waypoint_to_edit = {
            "id": db_vfr_waypoint_ids[aerodrome.code],
            "lat_degrees": aerodrome.lat_degrees,
            "lat_minutes": aerodrome.lat_minutes,
            "lat_seconds": aerodrome.lat_seconds,
            "lat_direction": aerodrome.lat_direction,
            "lon_degrees": aerodrome.lon_degrees,
            "lon_minutes": aerodrome.lon_minutes,
            "lon_seconds": aerodrome.lon_seconds,
            "lon_direction": aerodrome.lon_direction,
            "magnetic_variation": aerodrome.magnetic_variation
        }
        db.query(models.Waypoint)\
            .filter(models.Waypoint.id == waypoint_to_edit["id"])\
            .update(waypoint_to_edit, synchronize_session=False)

        vfr_waypoint_to_edit = {
            "waypoint_id": db_vfr_waypoint_ids[aerodrome.code],
            "code": aerodrome.code,
            "name": aerodrome.name,
            "creator_id": user_id,
            "hidden": aerodrome.hidden
        }
        db.query(models.VfrWaypoint)\
            .filter(models.VfrWaypoint.waypoint_id == vfr_waypoint_to_edit["waypoint_id"])\
            .update(vfr_waypoint_to_edit, synchronize_session=False)

        aerodrome_to_edit = {
            "id": db_vfr_waypoint_ids[aerodrome.code],
            "vfr_waypoint_id": db_vfr_waypoint_ids[aerodrome.code],
            "has_taf": aerodrome.has_taf,
            "has_metar": aerodrome.has_metar,
            "has_fds": aerodrome.has_fds,
            "elevation_ft": aerodrome.elevation_ft,
            "status_id": aerodrome.status
        }
        db.query(models.Aerodrome)\
            .filter(models.Aerodrome.id == aerodrome_to_edit["id"])\
            .update(aerodrome_to_edit, synchronize_session=False)

    db.commit()


@router.post("/registered-aerodrome", status_code=status.HTTP_201_CREATED, response_model=schemas.RegisteredAerodromeReturn)
async def post_registered_aerodrome(
    aerodrome: schemas.RegisteredAerodromeData,
    db: Session = Depends(get_db),
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

    status_exists = db.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    waypoint_result = await post_vfr_waypoint(waypoint=aerodrome, db=db, creator_id=user_id)

    new_aerodrome = models.Aerodrome(
        id=waypoint_result["id"],
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

    return {**new_aerodrome[0].__dict__, "status": new_aerodrome[1], **waypoint_result, "registered": True}


@router.post("/aerodrome-status", status_code=status.HTTP_201_CREATED, response_model=schemas.AerodromeStatusReturn)
async def post_aerodrome_status(
    aerodrome_status: str,
    db: Session = Depends(get_db),
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
            detail="Invalid aerodrome status format. Please use only letters, hyphens, and spaces. No line breaks, digits or special characters allowed."
        )

    clean_status = clean_string(aerodrome_status)

    already_exists = db.query(models.AerodromeStatus).filter_by(
        status=clean_status).first()
    if already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The aerodrome status youre trying to add, already exists, th ID is {already_exists.id}"
        )

    new_aerodrome_status = models.AerodromeStatus(status=clean_status)
    db.add(new_aerodrome_status)
    db.commit()
    db.refresh(new_aerodrome_status)

    return new_aerodrome_status


@router.put("/user/{id}", status_code=status.HTTP_200_OK, response_model=schemas.UserWaypointReturn)
async def edit_user_waypoint(
    id: int,
    waypoint: schemas.UserWaypointData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit User Waypoint Endpoint.

    Parameters: 
    - id (int): waypoint id
    - waypoint (dict): the waypoint object to be added.

    Returns: 
    Dic: dictionary with the waypoint data.

    Raise:
    - HTTPException (400): if waypoint already exists.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    user_waypoint_exists = db.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not user_waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The waypoint you're trying to update is not in the database."
        )

    duplicated_code = db.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.code == waypoint.code,
        not_(models.UserWaypoint.waypoint_id == id)
    )).first()

    if duplicated_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Another waypoint with code {waypoint.code} already exists. Try using a different code."
        )

    db.query(models.Waypoint).filter(models.Waypoint.id == id).update({
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

    db.query(models.UserWaypoint).filter(
        models.UserWaypoint.waypoint_id == id).update({
            "code": waypoint.code,
            "name": waypoint.name,
            "creator_id": user_id
        })

    db.commit()

    w = models.Waypoint
    u = models.UserWaypoint

    new_waypoint = db.query(w, u).join(
        w, u.waypoint_id == w.id).filter(u.waypoint_id == id).first()
    return {**new_waypoint[0].__dict__, **new_waypoint[1].__dict__}


@router.put("/vfr/{id}", status_code=status.HTTP_200_OK, response_model=schemas.VfrWaypointReturn)
async def edit_vfr_waypoint(
    id: int,
    waypoint: schemas.VfrWaypointData,
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

    user_id = await get_user_id_from_email(email=current_user.email, db=db)
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


@router.put("/registered-aerodrome/{id}", status_code=status.HTTP_200_OK, response_model=schemas.RegisteredAerodromeReturn)
async def edit_registered_aerodrome(
    id: int,
    aerodrome: schemas.RegisteredAerodromeData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Registered Aerodrome Endpoint.

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

    user_id = await get_user_id_from_email(email=current_user.email, db=db)
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

    return {**data[0].__dict__, **data[1].__dict__, **data[2].__dict__, "status": data[3], "registered": True}


@router.put("/private-aerodrome/{id}", status_code=status.HTTP_200_OK, response_model=schemas.PrivateAerodromeReturn)
async def edit_private_aerodrome(
    id: int,
    aerodrome: schemas.PrivateAerodromeData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Private Aerodrome Endpoint.

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
        models.Aerodrome.user_waypoint_id == id
    )
    if not aerodrome_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID, the waypoint ID you provided is not an aerodrome."
        )

    user_id = await get_user_id_from_email(email=current_user.email, db=db)
    user_waypoint_query = db.query(models.UserWaypoint).filter(
        and_(
            models.UserWaypoint.waypoint_id == id,
            models.UserWaypoint.creator_id == user_id
        )
    )
    if not user_waypoint_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID, you do not have permissio to edit this waypoint."
        )

    status_exists = db.query(models.AerodromeStatus).filter_by(
        id=aerodrome.status).first()
    if not status_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid status ID."
        )

    duplicated_code = db.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.code == aerodrome.code,
        not_(models.UserWaypoint.waypoint_id == id)
    )).first()

    if duplicated_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aerodrome with code {aerodrome.code} already exists. Try using a different code."
        )

    db.query(models.Waypoint).filter(
        models.Waypoint.id == id).update({
            "lat_degrees": aerodrome.lat_degrees,
            "lat_minutes": aerodrome.lat_minutes,
            "lat_seconds": aerodrome.lat_seconds,
            "lat_direction": aerodrome.lat_direction,
            "lon_degrees": aerodrome.lon_degrees,
            "lon_minutes": aerodrome.lon_minutes,
            "lon_seconds": aerodrome.lon_seconds,
            "lon_direction": aerodrome.lon_direction,
            "magnetic_variation": aerodrome.magnetic_variation
        })

    db.query(models.UserWaypoint).filter(
        models.UserWaypoint.waypoint_id == id).update({
            "code": aerodrome.code,
            "name": aerodrome.name,
            "creator_id": user_id
        })

    aerodrome_data = {
        "has_taf": aerodrome.has_taf,
        "has_metar": aerodrome.has_metar,
        "has_fds": aerodrome.has_fds,
        "elevation_ft": aerodrome.elevation_ft
    }

    db.query(models.Aerodrome).filter(
        models.Aerodrome.user_waypoint_id == id
    ).update({**aerodrome_data, "status_id": aerodrome.status})

    db.commit()

    s = models.AerodromeStatus
    a = models.Aerodrome
    u = models.UserWaypoint
    w = models.Waypoint

    data = db.query(w, u, a, s.status)\
        .join(u, w.id == u.waypoint_id)\
        .join(a, u.waypoint_id == a.user_waypoint_id)\
        .join(s, a.status_id == s.id)\
        .filter(w.id == id).first()

    return {**data[0].__dict__, **data[1].__dict__, **data[2].__dict__, "status": data[3], "registered": False}


@router.delete("/user/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_waypoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete User Waypoint.

    Parameters: 
    id (int): waypoint id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): waypoint not found.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db=db)
    waypoint_exists = db.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not waypoint_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The VFR waypoint you're trying to delete is not in the database."
        )

    deleted = db.query(models.Waypoint).filter(
        models.Waypoint.id == id).delete(synchronize_session=False)

    if not deleted:
        raise common_responses.internal_server_error()

    db.commit()


@router.delete("/registered", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vfr_waypoints_or_aerodromes(
    ids: List[int],
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete VFR Waypoint or Aerodrome.

    Parameters: 
    ids (List[int]): list of waypoint ids to be deleted.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): waypoint not found.
    - HTTPException (500): if there is a server error. 
    """

    waypoint_query = db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.waypoint_id.in_(ids))
    db_waypoint_ids = {w.waypoint_id for w in waypoint_query.all()}

    if not all(id in db_waypoint_ids for id in ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not all the VFR waypoint you're trying to delete are in the database."
        )

    for id in ids:
        deleted = db.query(models.Waypoint).filter(
            models.Waypoint.id == id).delete(synchronize_session=False)

        if not deleted:
            raise common_responses.internal_server_error()

    db.commit()


@router.delete("/aerodrome-status/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aerodrome_status(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Aerodrome Status.

    Parameters: 
    id (int): waypoint id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    status_query = db.query(models.AerodromeStatus).filter(
        models.AerodromeStatus.id == id)

    if not status_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The aerodrome status you're trying to delete is not in the database."
        )

    deleted = status_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db.commit()
