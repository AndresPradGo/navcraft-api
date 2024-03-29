"""
FastAPI runways router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
import pytz
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.config import get_table_header
from utils.db import get_db
from functions.data_processing import get_user_id_from_email, runways_are_unique

router = APIRouter(tags=["Runways"])


@router.get("", status_code=status.HTTP_200_OK, response_model=List[schemas.RunwayReturn])
def get_all_runways(
    runway_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Returns all runways (only admin users can use this endpoint)
    """

    v = models.VfrWaypoint
    a = models.Aerodrome
    r = models.Runway
    s = models.RunwaySurface

    aerodromes = db_session.query(a.id, v.code)\
        .filter(a.vfr_waypoint is not None)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id).all()
    aerodrome_ids = [a[0] for a in aerodromes]
    aerodrome_codes = {a[0]: a[1] for a in aerodromes}

    runways = db_session.query(r, s.surface)\
        .filter(and_(
            models.Runway.aerodrome_id.in_(aerodrome_ids),
            or_(
                not_(runway_id),
                models.Runway.id == runway_id
            )
        ))\
        .join(s, r.surface_id == s.id).all()

    runways_return = [schemas.RunwayReturn(
        id=r[0].id,
        length_ft=r[0].length_ft,
        landing_length_ft=r[0].landing_length_ft,
        intersection_departure_length_ft=r[0].intersection_departure_length_ft,
        number=r[0].number,
        position=r[0].position,
        surface_id=r[0].surface_id,
        aerodrome_id=r[0].aerodrome_id,
        surface=r[1],
        aerodrome=aerodrome_codes[r[0].aerodrome_id],
        created_at_utc=pytz.timezone('UTC').localize((r[0].created_at)),
        last_updated_utc=pytz.timezone('UTC').localize((r[0].last_updated))
    ) for r in runways]

    runways_return.sort(key=lambda r: (
        r.aerodrome, r.number, r.position))

    return runways_return


@router.get("/csv", status_code=status.HTTP_200_OK)
def get_csv_file_with_all_runways(
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Returns a CSV File with all runways (only admin users can use this endpoint)
    """

    a = models.Aerodrome
    v = models.VfrWaypoint

    aerodromes = [{
        "id": a.id,
        "code": v.code,
        "name": v.name
    } for a, v in db_session.query(a, v)
        .filter(a.user_waypoint_id.is_(None))
        .join(v, a.vfr_waypoint_id == v.waypoint_id).all()]

    aerodrome_ids = [item["id"] for item in aerodromes]
    aerodrome_codes = {a["id"]: a["code"] for a in aerodromes}

    runways = db_session.query(models.Runway)\
        .filter(models.Runway.aerodrome_id.in_(aerodrome_ids)).all()
    surfaces = db_session.query(models.RunwaySurface).all()

    runway_headers = get_table_header("runways")
    aerodrome_headers = get_table_header("aerodrome_codes")
    surface_headers = get_table_header("runway_surface_ids")

    files_data = [
        {
            "name": "runways.csv",
            "data": sorted(
                [{
                    runway_headers["aerodrome"]: aerodrome_codes[r.aerodrome_id],
                    runway_headers["number"]: r.number,
                    runway_headers["position"]: r.position,
                    runway_headers["length_ft"]: r.length_ft,
                    runway_headers["landing_length_ft"]: r.length_ft - r.landing_length_ft if r.landing_length_ft is not None else "",
                    runway_headers["intersection_departure_length_ft"]: r.intersection_departure_length_ft,
                    runway_headers["surface_id"]: r.surface_id,
                } for r in runways],
                key=lambda r: (
                    r[runway_headers["aerodrome"]],
                    r[runway_headers["number"]],
                    r[runway_headers["position"]]
                )
            ) if len(runways) else [{
                runway_headers["aerodrome_id"]: "",
                runway_headers["number"]: "",
                runway_headers["position"]: "",
                runway_headers["length_ft"]: "",
                runway_headers["landing_length_ft"]: "",
                runway_headers["intersection_departure_length_ft"]: "",
                runway_headers["surface_id"]: "",
            }]
        },
        {
            "name": "aerodrome_codes.csv",
            "data": sorted(
                [{
                    aerodrome_headers["code"]: a["code"],
                    aerodrome_headers["name"]: a["name"]
                } for a in aerodromes],
                key=lambda a: a[aerodrome_headers["code"]]
            ) if len(aerodromes) else [{
                aerodrome_headers["code"]: "",
                aerodrome_headers["name"]: ""
            }]
        },
        {
            "name": "runway_surface_ids.csv",
            "data": sorted(
                [{
                    surface_headers["id"]: s.id,
                    surface_headers["surface"]: s.surface
                } for s in surfaces],
                key=lambda s: s[surface_headers["id"]]
            ) if len(surfaces) else [{
                surface_headers["id"]: "",
                surface_headers["surface"]: ""
            }]
        }
    ]

    zip_buffer = csv.zip_csv_files_from_data_list(files_data)
    response = StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="runways_data.zip"',
            "filename": "runways_data.zip"
        }
    )

    return response


@router.get(
    "/surfaces",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.RunwaySurfaceReturn]
)
def get_all_runway_surfaces(
    runway_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Returns all runway surfaces
    """

    return db_session.query(models.RunwaySurface).filter(or_(
        not_(runway_id),
        models.RunwaySurface.id == runway_id
    )).order_by(models.RunwaySurface.surface).all()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=schemas.RunwayReturn)
def post_runway(
    runway_data: schemas.RunwayData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Creates a new runway for a given aerodrome
    """

    # Check if aerodrome exists
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    aerodrome = db_session.query(models.Aerodrome).filter_by(
        id=runway_data.aerodrome_id).first()

    if not aerodrome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid Aerodrome ID."
        )

    # Check if user has permission to update this aerodrome
    no_permission_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"You do not have permission to update aerodrome with id {runway_data.aerodrome_id}."
    )

    aerodrome_is_registered = aerodrome.vfr_waypoint
    user_is_active_admin = current_user.is_active and current_user.is_admin

    if aerodrome_is_registered and not user_is_active_admin:
        raise no_permission_exception

    aerodrome_created_by_user = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == runway_data.aerodrome_id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not aerodrome_is_registered and not aerodrome_created_by_user:
        raise no_permission_exception

    # Check if surface exists
    surface_exists = db_session.query(models.RunwaySurface).filter_by(
        id=runway_data.surface_id).first()
    if not surface_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid runway surface ID."
        )

    # Check if runway already exists.
    runway_esxists = db_session.query(models.Runway).filter(and_(
        models.Runway.aerodrome_id == runway_data.aerodrome_id,
        models.Runway.number == runway_data.number,
        or_(
            models.Runway.position.is_(None),
            runway_data.position is None,
            models.Runway.position == runway_data.position
        )
    )).first()
    if runway_esxists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The runway you are trying to add, already exists."
        )

    # Post runway
    new_runway = models.Runway(
        length_ft=runway_data.length_ft,
        landing_length_ft=runway_data.landing_length_ft,
        intersection_departure_length_ft=runway_data.intersection_departure_length_ft,
        number=runway_data.number,
        position=runway_data.position,
        aerodrome_id=runway_data.aerodrome_id,
        surface_id=runway_data.surface_id
    )

    db_session.add(new_runway)
    db_session.commit()
    db_session.refresh(new_runway)

    # Return runway data
    u = models.UserWaypoint
    v = models.VfrWaypoint
    a = models.Aerodrome
    r = models.Runway
    s = models.RunwaySurface

    runway_result = db_session.query(r, s.surface)\
        .filter(r.id == new_runway.id)\
        .join(s, r.surface_id == s.id).first()

    aerodrome_result = db_session.query(a, v.code).filter(a.id == new_runway.aerodrome_id)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id).first() if aerodrome_is_registered else\
        db_session.query(a, u.code).filter(a.id == new_runway.aerodrome_id)\
        .join(u, a.user_waypoint_id == u.waypoint_id).first()

    return {
        "aerodrome": aerodrome_result[1],
        **runway_result[0].__dict__,
        "surface": runway_result[1],
        "created_at_utc": pytz.timezone('UTC').localize((runway_result[0].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((runway_result[0].last_updated))
    }


@router.post("/csv", status_code=status.HTTP_204_NO_CONTENT)
async def manage_runways_with_csv_file(
    csv_file: UploadFile,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Manages runways (only admin users can use this endpoint)

    Usage:
    - Download the Runways csv-list, from the "Get Csv File With All Runways" endpoint
    - Use this file to update the list in the desired way
    - New columns can be added for your reference, but they won't be considered for updating the 
      data in the database
    - Do not delete or edit the headers of the existing colums in any way, 
      or the file will be rejected
    - Enter all data in the correct colums to ensure data integrity
    - Make sure there are no typos or repeated entries
    - After getting a 204 response, download csv list again to check it has been uploaded correctly

    NOTE: This endpoint will delete all runways in the database for the given aerodromes,
    and will post new data-entries


    Other Parameters: 
    - csv-file (UploadFile schema): csv file with runway data
    """

    # Check and decode csv-file
    csv.check_format(csv_file)

    # Get list of schemas
    dict_list = await csv.extract_data(file=csv_file)
    headers = get_table_header("runways")

    # Check all aerodrome codes are valid
    a = models.Aerodrome
    v = models.VfrWaypoint

    try:
        aerodrome_codes = {r[headers["aerodrome"]].strip().upper()
                           for r in dict_list}
    except KeyError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'CSV File is missing the header "{error}"'
        )

    aerodrome_objects = db_session.query(a, v)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id)\
        .filter(v.code.in_(aerodrome_codes))\
        .all()

    aerodrome_ids_in_db = {v.code: v.waypoint_id for _, v in aerodrome_objects}

    if not len(aerodrome_codes) == len(set(aerodrome_ids_in_db.keys())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some of the aerodromes are not in the database."
        )

    try:
        data_list = [schemas.RunwayData(
            aerodrome_id=int(float(aerodrome_ids_in_db[r[headers["aerodrome"]].strip(
            ).upper()])),
            number=int(float(r[headers["number"]])),
            position=None if not r[headers["position"]]
            or r[headers["position"]].isspace()
            else r[headers["position"]],
            length_ft=int(float(r[headers["length_ft"]])),
            landing_length_ft=None if not r[headers["landing_length_ft"]]
            or r[headers["landing_length_ft"]].isspace()
            else int(float(r[headers["length_ft"]])) - int(float(r[headers["landing_length_ft"]])),
            intersection_departure_length_ft=None if not r[headers["intersection_departure_length_ft"]]
            or r[headers["intersection_departure_length_ft"]].isspace()
            else int(float(r[headers["intersection_departure_length_ft"]])),
            surface_id=int(float(r[headers["surface_id"]]))
        ) for r in dict_list]
    except KeyError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'CSV File is missing the header "{error}"'
        )
    except (ValidationError) as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    # Check there are no repeated runways
    if not runways_are_unique(data_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Make sure all runways in the list are unique."
        )

    # Check all surface ids are valid
    surface_ids = {r.surface_id for r in data_list}
    surfaces_in_db = db_session.query(models.RunwaySurface).filter(
        models.RunwaySurface.id.in_(surface_ids)).all()
    if not len(surface_ids) == len(surfaces_in_db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some of the surface IDs are not valid."
        )

    # Delete Runways
    _ = db_session.query(models.Runway).filter(models.Runway.aerodrome_id.in_(
        list(aerodrome_ids_in_db.values()))).delete(synchronize_session="evaluate")

    # Add data
    for runway in data_list:
        new_runway = models.Runway(
            aerodrome_id=runway.aerodrome_id,
            number=runway.number,
            position=runway.position,
            length_ft=runway.length_ft,
            landing_length_ft=runway.landing_length_ft,
            intersection_departure_length_ft=runway.intersection_departure_length_ft,
            surface_id=runway.surface_id
        )
        db_session.add(new_runway)

    db_session.commit()


@router.post(
    "/surface",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.RunwaySurfaceReturn
)
def post_runway_surface(
    surface_data: schemas.RunwaySurfaceData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Creates a new runway surface (only admin users can use this endpoint)
    """

    surface_exists = db_session.query(models.RunwaySurface).filter(
        models.RunwaySurface.surface == surface_data.surface).first()

    if surface_exists:
        msg = f"{surface_data.surface} is already in the database."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    new_surface = models.RunwaySurface(
        surface=surface_data.surface
    )
    db_session.add(new_surface)
    db_session.commit()
    db_session.refresh(new_surface)

    return new_surface


@router.put("/{runway_id}", status_code=status.HTTP_200_OK, response_model=schemas.RunwayReturn)
def edit_runway(
    runway_id: int,
    runway_data: schemas.RunwayDataEdit,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edits a runway
    """
    # Check if runway exists
    runway_query = db_session.query(models.Runway).filter(
        models.Runway.id == runway_id)
    if not runway_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid runway ID."
        )

    # Check if user has permission to update this aerodrome
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    aerodrome_id = runway_query.first().aerodrome_id

    no_permission_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"You do not have permission to update aerodrome with id {aerodrome_id}."
    )

    aerodrome_is_registered = db_session.query(models.Aerodrome.vfr_waypoint_id).filter_by(
        id=aerodrome_id).first()[0] is not None
    user_is_active_admin = current_user.is_active and current_user.is_admin

    if aerodrome_is_registered and not user_is_active_admin:
        raise no_permission_exception

    aerodrome_created_by_user = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == aerodrome_id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not aerodrome_is_registered and not aerodrome_created_by_user:
        raise no_permission_exception

    # Check if surface exists
    surface_exists = db_session.query(models.RunwaySurface).filter_by(
        id=runway_data.surface_id).first()
    if not surface_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid runway surface ID."
        )

    # Check if another runway with same data exists.
    runway_esxists = db_session.query(models.Runway).filter(and_(
        models.Runway.aerodrome_id == aerodrome_id,
        not_(models.Runway.id == runway_id),
        models.Runway.number == runway_data.number,
        or_(
            models.Runway.position.is_(None),
            runway_data.position is None,
            models.Runway.position == runway_data.position
        )
    )).first()
    if runway_esxists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The runway you are trying to add, already exists."
        )

    runway_query.update({
        "length_ft": runway_data.length_ft,
        "landing_length_ft": runway_data.landing_length_ft,
        "intersection_departure_length_ft": runway_data.intersection_departure_length_ft,
        "number": runway_data.number,
        "position": runway_data.position,
        "surface_id": runway_data.surface_id
    })
    db_session.commit()

    u = models.UserWaypoint
    v = models.VfrWaypoint
    a = models.Aerodrome
    r = models.Runway
    s = models.RunwaySurface

    runway_result = db_session.query(r, s.surface)\
        .filter(r.id == runway_id)\
        .join(s, r.surface_id == s.id).first()

    aerodrome_result = db_session.query(a, v.code).filter(a.id == aerodrome_id)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id).first() if aerodrome_is_registered else\
        db_session.query(a, u.code).filter(a.id == aerodrome_id)\
        .join(u, a.user_waypoint_id == u.waypoint_id).first()

    return {
        "aerodrome": aerodrome_result[1],
        **runway_result[0].__dict__,
        "surface": runway_result[1],
        "created_at_utc": pytz.timezone('UTC').localize((runway_result[0].created_at)),
        "last_updated_utc": pytz.timezone('UTC').localize((runway_result[0].last_updated))
    }


@router.put(
    "/surface/{surface_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RunwaySurfaceReturn
)
def edit_runway_surface(
    surface_id: int,
    surface_data: schemas.RunwaySurfaceData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edits a runway surface (only admin users can use this endpoint)
    """
    surface_exists = db_session.query(models.RunwaySurface).filter(and_(
        models.RunwaySurface.surface == surface_data.surface,
        not_(models.RunwaySurface.id == surface_id)
    )).first()

    if surface_exists:
        msg = f"{surface_data.surface} is already in the database."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    surface_query = db_session.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == surface_id
    )

    if not surface_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The surface ID provided does not exist in the database."
        )

    surface_query.update(surface_data.model_dump())
    db_session.commit()

    new_surface = db_session.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == surface_id
    ).first()

    return new_surface


@router.delete("/{runway_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_runway(
    runway_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Deletes a runways
    """

    # Check if runway exists
    db_runway = db_session.query(
        models.Runway).filter(models.Runway.id == runway_id).first()

    if db_runway is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Runway you're trying to delete is not in the database."
        )

    # Define some variables
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    user_is_active_admin = current_user.is_active and current_user.is_admin

    # Check if user has permission to update this aerodrome
    runway_query = db_session.query(models.Runway).filter_by(id=runway_id)
    aerodrome_id = runway_query.first().aerodrome_id

    no_permission_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"You do not have permission to update aerodrome with id {aerodrome_id}."
    )

    aerodrome_is_registered = db_session.query(models.Aerodrome.vfr_waypoint_id).filter_by(
        id=aerodrome_id).first()[0] is not None

    if aerodrome_is_registered and not user_is_active_admin:
        raise no_permission_exception

    aerodrome_created_by_user = db_session.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == aerodrome_id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not aerodrome_is_registered and not aerodrome_created_by_user:
        raise no_permission_exception

    deleted = runway_query.delete(synchronize_session=False)

    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()


@router.delete("/surface/{surface_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_runway_surface(
    surface_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Deletes a runway surface (only admin users can use this endpoint)
    """

    surface_query = db_session.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == surface_id)

    if not surface_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The runway surface you're trying to delete is not in the database."
        )

    runway_with_surface = db_session.query(models.Runway).filter(
        models.Runway.surface_id == surface_id).first()
    if runway_with_surface:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This surface cannot be deleted, as there are runways currently using it."
        )

    aircraft_performance_with_surface = db_session.query(models.SurfacePerformanceDecrease).\
        filter(models.SurfacePerformanceDecrease.surface_id == surface_id).first()
    if aircraft_performance_with_surface:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This surface cannot be deleted, as it is being used by aircraft performance."
        )

    deleted = surface_query.delete(synchronize_session=False)

    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()
