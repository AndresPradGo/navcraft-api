"""
FastAPI manage vfr waypoints router

This module defines the FastAPI endpoints to manage vfr waypoints using csv files.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import csv_tools as csv
from utils.config import get_table_header
from utils.db import get_db
from functions.data_processing import get_user_id_from_email
from functions.navigation import get_magnetic_variation_for_waypoint

router = APIRouter(tags=["Manage Waypoints"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_csv_file_with_all_vfr_waypoints(
    db_session: Session = Depends(get_db),
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

    aerodromes = [item[0] for item in db_session.query(
        a.vfr_waypoint_id).filter(not_(a.vfr_waypoint_id.is_(None))).all()]

    query_results = db_session.query(w, v)\
        .filter(not_(w.id.in_(aerodromes)))\
        .join(v, w.id == v.waypoint_id).order_by(v.name).all()

    table_name = "vfr_waypoints"
    headers = get_table_header(table_name)

    data = [{
        headers["code"]: v.code,
        headers["name"]: v.name,
        headers["lat_degrees"]: w.lat_degrees,
        headers["lat_minutes"]: w.lat_minutes,
        headers["lat_seconds"]: w.lat_seconds,
        headers["lat_direction"]: w.lat_direction,
        headers["lon_degrees"]: w.lon_degrees,
        headers["lon_minutes"]: w.lon_minutes,
        headers["lon_seconds"]: w.lon_seconds,
        headers["lon_direction"]: w.lon_direction,
        headers["magnetic_variation"]: w.magnetic_variation,
        headers["hidden"]: v.hidden
    } for w, v in query_results] if len(query_results) else [
        {
            headers["code"]: "",
            headers["name"]: "",
            headers["lat_degrees"]: "",
            headers["lat_minutes"]: "",
            headers["lat_seconds"]: "",
            headers["lat_direction"]: "",
            headers["lon_degrees"]: "",
            headers["lon_minutes"]: "",
            headers["lon_seconds"]: "",
            headers["lon_direction"]: "",
            headers["magnetic_variation"]: "",
            headers["hidden"]: ""
        }
    ]

    buffer = csv.list_to_buffer(data=data)

    response = StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{table_name}.csv"'
    response.headers["filename"] = f'{table_name}.csv'
    return response


@router.get("/aerodromes", status_code=status.HTTP_200_OK)
async def get_csv_file_with_all_aerodromes(
    db_session: Session = Depends(get_db),
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

    aerodromes = db_session.query(w, v, a)\
        .filter(not_(a.vfr_waypoint_id.is_(None)))\
        .join(v, w.id == v.waypoint_id)\
        .join(a, v.waypoint_id == a.vfr_waypoint_id).order_by(v.name).all()

    table_name = "aerodromes"
    headers = get_table_header(table_name)

    data = [{
        headers["code"]: v.code,
        headers["name"]: v.name,
        headers["lat_degrees"]: w.lat_degrees,
        headers["lat_minutes"]: w.lat_minutes,
        headers["lat_seconds"]: w.lat_seconds,
        headers["lat_direction"]: w.lat_direction,
        headers["lon_degrees"]: w.lon_degrees,
        headers["lon_minutes"]: w.lon_minutes,
        headers["lon_seconds"]: w.lon_seconds,
        headers["lon_direction"]: w.lon_direction,
        headers["elevation_ft"]: a.elevation_ft,
        headers["magnetic_variation"]: w.magnetic_variation,
        headers["has_taf"]: a.has_taf,
        headers["has_metar"]: a.has_metar,
        headers["has_fds"]: a.has_fds,
        headers["hidden"]: v.hidden,
        headers["status_id"]: a.status_id
    } for w, v, a in aerodromes] if len(aerodromes) else [{
        headers["code"]: "",
        headers["name"]: "",
        headers["lat_degrees"]: "",
        headers["lat_minutes"]: "",
        headers["lat_seconds"]: "",
        headers["lat_direction"]: "",
        headers["lon_degrees"]: "",
        headers["lon_minutes"]: "",
        headers["lon_seconds"]: "",
        headers["lon_direction"]: "",
        headers["elevation_ft"]: "",
        headers["magnetic_variation"]: "",
        headers["has_taf"]: "",
        headers["has_metar"]: "",
        headers["has_fds"]: "",
        headers["hidden"]: "",
        headers["status_id"]: ""
    }]

    buffer = csv.list_to_buffer(data=data)

    response = StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{table_name}.csv"'
    response.headers["filename"] = f'{table_name}.csv'
    return response


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def manage_vfr_waypoints_with_csv_file(
    csv_file: UploadFile,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Manage VFR Waypoints Endpoint.

    Usage:
    - Download the VFR-Waypoint csv-list, from the "Get Csv File With All Vfr Waypoints" endpoint.
    - Use this file to update the list in the desired way.
    - New columns can be added for your reference, but they won't be considered for updating the 
      data in the database. 
    - Do not delete or edit the headers of the existing colums in any way, or the file 
      will be rejected.
    - Enter all data in the correct colum to ensure data integrity.
    - Make sure there are no typos or repeated entries.
    - After getting a 204 response, download csv list again to check it has been uploaded correctly.

    NOTE: This endpoint will post new data-entries, and update existing ones, 
    but it will not delete any entries already in the database. To delete existing 
    data-entries, use the appropriate delete endpoint.

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
    table_name = "vfr_waypoints"
    headers = get_table_header(table_name)
    try:
        data_list = [schemas.VfrWaypointData(
            code=v[headers["code"]],
            name=v[headers["name"]],
            lat_degrees=int(float(v[headers["lat_degrees"]])),
            lat_minutes=int(float(v[headers["lat_minutes"]])),
            lat_seconds=int(float(v[headers["lat_seconds"]])),
            lat_direction=v[headers["lat_direction"]],
            lon_degrees=int(float(v[headers["lon_degrees"]])),
            lon_minutes=int(float(v[headers["lon_minutes"]])),
            lon_seconds=int(float(v[headers["lon_seconds"]])),
            lon_direction=v[headers["lon_direction"]],
            magnetic_variation=None if headers["magnetic_variation"] not in v
            or not v[headers["magnetic_variation"]]
            or v[headers["magnetic_variation"]].isspace()
            else v[headers["magnetic_variation"]],
            hidden=v[headers["hidden"]]
        ) for v in await csv.extract_data(file=csv_file)]
    except KeyError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'CSV File is missing the header "{error}"'
        )
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    # Check there are no repeated codes
    codes_set = {v.code for v in data_list}
    if not len(data_list) == len(set(codes_set)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Make sure all waypoints are unique."
        )

    # Find waypoints already in database
    db_vfr_waypoints = db_session.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.code.in_(codes_set)).all()
    db_vfr_waypoint_ids = {v.code: v.waypoint_id for v in db_vfr_waypoints}

    # Divide list into data to add and data to edit
    data_to_add = [v for v in filter(
        lambda i: not i.code in list(db_vfr_waypoint_ids.keys()), data_list)]
    data_to_edit = [v for v in filter(
        lambda i: i.code in list(db_vfr_waypoint_ids.keys()), data_list)]

    # Add data
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

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
            magnetic_variation=waypoint.magnetic_variation
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
            creator_id=user_id
        )
        db_session.add(new_vfr_waypoint)
        db_session.commit()

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
            "lon_direction": waypoint.lon_direction
        }
        if waypoint.magnetic_variation is not None:
            waypoint_to_edit["magnetic_variation"] = waypoint.magnetic_variation

        db_session.query(models.Waypoint)\
            .filter(models.Waypoint.id == waypoint_to_edit["id"])\
            .update(waypoint_to_edit, synchronize_session=False)

        vfr_waypoint_to_edit = {
            "waypoint_id": db_vfr_waypoint_ids[waypoint.code],
            "code": waypoint.code,
            "name": waypoint.name,
            "creator_id": user_id,
            "hidden": waypoint.hidden
        }
        db_session.query(models.VfrWaypoint)\
            .filter(models.VfrWaypoint.waypoint_id == vfr_waypoint_to_edit["waypoint_id"])\
            .update(vfr_waypoint_to_edit, synchronize_session=False)

    db_session.commit()


@router.post("/aerodromes", status_code=status.HTTP_204_NO_CONTENT)
async def manage_registered_aerodrome_with_csv_file(
    csv_file: UploadFile,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Manage Registered Aerodrome Endpoint.

    Usage:
    - Download the Registered-Aerodrome csv-list, from the 
      "Get Csv File With All Aerodrome" endpoint.
    - Use this file to update the list in the desired way.
    - New columns can be added for your reference, but they won't be considered for updating the 
      data in the database. 
    - Do not delete or edit the headers of the existing colums in any way, 
      or the file will be rejected.
    - Enter all data in the correct colum to ensure data integrity.
    - Make sure there are no typos or repeated entries.
    - After getting a 204 response, download csv list again to check it has been uploaded correctly.

    NOTE: This endpoint will post new data-entries, and update existing ones, 
    but it will not delete any entries already in the database. To delete 
    existing data-entries, use the appropriate delete endpoint.

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
    table_name = "aerodromes"
    headers = get_table_header(table_name)
    try:
        data_list = [schemas.RegisteredAerodromeData(
            code=a[headers["code"]],
            name=a[headers["name"]],
            lat_degrees=int(float(a[headers["lat_degrees"]])),
            lat_minutes=int(float(a[headers["lat_minutes"]])),
            lat_seconds=int(float(a[headers["lat_seconds"]])),
            lat_direction=a[headers["lat_direction"]],
            lon_degrees=int(float(a[headers["lon_degrees"]])),
            lon_minutes=int(float(a[headers["lon_minutes"]])),
            lon_seconds=int(float(a[headers["lon_seconds"]])),
            lon_direction=a[headers["lon_direction"]],
            magnetic_variation=None if headers["magnetic_variation"] not in a
            or not a[headers["magnetic_variation"]]
            or a[headers["magnetic_variation"]].isspace()
            else a[headers["magnetic_variation"]],
            status=a[headers["status_id"]],
            elevation_ft=int(float(a[headers["elevation_ft"]])),
            has_taf=a[headers["has_taf"]],
            has_metar=a[headers["has_metar"]],
            has_fds=a[headers["has_fds"]],
            hidden=a[headers["hidden"]]
        ) for a in await csv.extract_data(file=csv_file)]
    except KeyError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'CSV File is missing the header "{error}"'
        )
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    # Check there are no repeated codes
    codes_set = {v.code for v in data_list}
    if not len(data_list) == len(set(codes_set)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Make sure all aerodromes are unique."
        )

    # Check status ids are corret
    status_ids = {a.status for a in data_list}
    status_ids_id_db = [s.id for s in db_session.query(models.AerodromeStatus)
                        .filter(models.AerodromeStatus.id.in_(status_ids)).all()]
    if not len(status_ids) == len(status_ids_id_db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="please make sure all the aerodrome status IDs are correct."
        )
    # Find waypoints already in database
    db_vfr_waypoints = db_session.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.code.in_(codes_set)).all()
    db_vfr_waypoint_ids = {v.code: v.waypoint_id for v in db_vfr_waypoints}

    # Divide list into data to add and data to edit
    data_to_add = [v for v in filter(
        lambda i: not i.code in list(db_vfr_waypoint_ids.keys()), data_list)]
    data_to_edit = [v for v in filter(
        lambda i: i.code in list(db_vfr_waypoint_ids.keys()), data_list)]

    # Add data
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)

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
        new_waypoint.magnetic_variation = get_magnetic_variation_for_waypoint(
            waypoint=new_waypoint,
            db_session=db_session
        )

        db_session.add(new_waypoint)
        db_session.commit()
        db_session.refresh(new_waypoint)

        new_vfr_waypoint = models.VfrWaypoint(
            waypoint_id=new_waypoint.id,
            code=aerodrome.code,
            name=aerodrome.name,
            hidden=aerodrome.hidden,
            creator_id=user_id
        )
        db_session.add(new_vfr_waypoint)

        new_aerodrome = models.Aerodrome(
            id=new_waypoint.id,
            vfr_waypoint_id=new_waypoint.id,
            has_taf=aerodrome.has_taf,
            has_metar=aerodrome.has_metar,
            has_fds=aerodrome.has_fds,
            elevation_ft=aerodrome.elevation_ft,
            status_id=aerodrome.status
        )
        db_session.add(new_aerodrome)
        db_session.commit()

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
        }
        if aerodrome.magnetic_variation is not None:
            waypoint_to_edit["magnetic_variation"] = aerodrome.magnetic_variation

        db_session.query(models.Waypoint)\
            .filter(models.Waypoint.id == waypoint_to_edit["id"])\
            .update(waypoint_to_edit, synchronize_session=False)

        vfr_waypoint_to_edit = {
            "waypoint_id": db_vfr_waypoint_ids[aerodrome.code],
            "code": aerodrome.code,
            "name": aerodrome.name,
            "creator_id": user_id,
            "hidden": aerodrome.hidden
        }
        db_session.query(models.VfrWaypoint)\
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
        db_session.query(models.Aerodrome)\
            .filter(models.Aerodrome.id == aerodrome_to_edit["id"])\
            .update(aerodrome_to_edit, synchronize_session=False)

    db_session.commit()
