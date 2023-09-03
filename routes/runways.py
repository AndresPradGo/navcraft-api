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
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.db import get_db
from utils.functions import get_user_id_from_email, runways_are_unique, get_table_header

router = APIRouter(tags=["Runways"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[schemas.RunwayReturn])
async def get_all_runways(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Get All Runways Endpoint.

    Parameters: None

    Returns: 
    - list: list of runway dictionaries.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    v = models.VfrWaypoint
    a = models.Aerodrome
    r = models.Runway
    s = models.RunwaySurface

    aerodromes = db.query(a.id, v.code)\
        .filter(a.vfr_waypoint is not None)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id).all()
    aerodrome_ids = [a[0] for a in aerodromes]
    aerodrome_codes = {a[0]: a[1] for a in aerodromes}

    runways = db.query(r, s.surface)\
        .filter(and_(
            models.Runway.aerodrome_id.in_(aerodrome_ids),
            or_(
                not_(id),
                models.Runway.id == id
            )
        ))\
        .join(s, r.surface_id == s.id).all()

    runways_return = [schemas.RunwayReturn(
        id=r[0].id,
        length_ft=r[0].length_ft,
        number=r[0].number,
        position=r[0].position,
        surface_id=r[0].surface_id,
        aerodrome_id=r[0].aerodrome_id,
        surface=r[1],
        aerodrome=aerodrome_codes[r[0].aerodrome_id]
    ) for r in runways]

    return runways_return


@router.get("/csv", status_code=status.HTTP_200_OK)
async def get_csv_file_with_all_runways(
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Get CSV File With All Runways Endpoint.

    Parameters: None

    Returns: 
    - Zip folder: zip folder with 3 files:
       - runways.csv
       - aerodrome_codes.csv
       - surface_ids.csv

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    a = models.Aerodrome
    v = models.VfrWaypoint

    aerodromes = [{
        "id": a.id,
        "code": v.code,
        "name": v.name
    } for a, v in db.query(a, v)
        .filter(a.user_waypoint_id.is_(None))
        .join(v, a.vfr_waypoint_id == v.waypoint_id).all()]

    aerodrome_ids = [item["id"] for item in aerodromes]
    aerodrome_codes = {a["id"]: a["code"] for a in aerodromes}

    runways = db.query(models.Runway)\
        .filter(models.Runway.aerodrome_id.in_(aerodrome_ids)).all()
    surfaces = db.query(models.RunwaySurface).all()

    runway_headers = get_table_header("runways")
    aerodrome_headers = get_table_header("aerodrome_codes")
    surface_headers = get_table_header("runway_surface_ids")

    files_data = [
        {
            "name": "runways.csv",
            "data": [{
                runway_headers["aerodrome"]: aerodrome_codes[r.aerodrome_id],
                runway_headers["number"]: r.number,
                runway_headers["position"]: r.position,
                runway_headers["length_ft"]: r.length_ft,
                runway_headers["surface_id"]: r.surface_id,
            } for r in runways] if len(runways) else [{
                runway_headers["aerodrome_id"]: "",
                runway_headers["number"]: "",
                runway_headers["position"]: "",
                runway_headers["length_ft"]: "",
                runway_headers["surface_id"]: "",
            }]
        },
        {
            "name": "aerodrome_codes.csv",
            "data": [{
                aerodrome_headers["code"]: a["code"],
                aerodrome_headers["name"]: a["name"]
            } for a in aerodromes] if len(aerodromes) else [{
                aerodrome_headers["code"]: "",
                aerodrome_headers["name"]: ""
            }]
        },
        {
            "name": "runway_surface_ids.csv",
            "data": [{
                surface_headers["id"]: s.id,
                surface_headers["surface"]: s.surface
            } for s in surfaces] if len(surfaces) else [{
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
            "Content-Disposition": 'attachment; filename="runways_data.zip"'}
    )

    return response


@router.get(
    "/surfaces",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.RunwaySurfaceReturn]
)
async def get_all_runway_surfaces(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get All Runway Surfaces Endpoint.

    Parameters: None

    Returns: 
    - list: list of runway syrface dictionaries.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    return db.query(models.RunwaySurface).filter(or_(
        not_(id),
        models.RunwaySurface.id == id
    )).all()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.RunwayReturn)
async def post_runway_(
    runway_data: schemas.RunwayData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post Runway Endpoint.

    Parameters: 
    - runway_data (dict): the runway object to be added.

    Returns: 
    Dic: dictionary with the runway data.

    Raise:
    - HTTPException (400): if runway already exists.
    - HTTPException (500): if there is a server error. 
    """

    # Check if aerodrome exists
    user_id = await get_user_id_from_email(email=current_user.email, db=db)
    aerodrome = db.query(models.Aerodrome).filter_by(
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

    aerodrome_created_by_user = db.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == runway_data.aerodrome_id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not aerodrome_is_registered and not aerodrome_created_by_user:
        raise no_permission_exception

    # Check if surface exists
    surface_exists = db.query(models.RunwaySurface).filter_by(
        id=runway_data.surface_id).first()
    if not surface_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid runway surface ID."
        )

    # Check if runway already exists.
    runway_esxists = db.query(models.Runway).filter(and_(
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
        number=runway_data.number,
        position=runway_data.position,
        aerodrome_id=runway_data.aerodrome_id,
        surface_id=runway_data.surface_id
    )

    db.add(new_runway)
    db.commit()
    db.refresh(new_runway)

    # Return runway data
    u = models.UserWaypoint
    v = models.VfrWaypoint
    a = models.Aerodrome
    r = models.Runway
    s = models.RunwaySurface

    runway_result = db.query(r, s.surface)\
        .filter(r.id == new_runway.id)\
        .join(s, r.surface_id == s.id).first()

    aerodrome_result = db.query(a, v.code).filter(a.id == new_runway.aerodrome_id)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id).first() if aerodrome_is_registered else\
        db.query(a, u.code).filter(a.id == new_runway.aerodrome_id)\
        .join(u, a.user_waypoint_id == u.waypoint_id).first()

    return {"aerodrome": aerodrome_result[1], **runway_result[0].__dict__, "surface": runway_result[1]}


@router.post("/csv", status_code=status.HTTP_204_NO_CONTENT)
async def manage_runways_with_csv_file(
    csv_file: UploadFile,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Manage Runways Endpoint.

    Usage:
    - Download the Runways csv-list, from the "Get Csv File With All Runways" endpoint.
    - Use this file to update the list in the desired way.
    - New columns can be added for your reference, but they won't be considered for updating the 
      data in the database. 
    - Do not delete or edit the headers of the existing colums in any way, or the file will be rejected.
    - Enter all data in the correct colums to ensure data integrity.
    - Make sure there are no typos or repeated entries.
    - After getting a 204 response, download csv list again to check it has been uploaded correctly.

    NOTE: This endpoint will delete all runways in the database for the given aerodromes, and will post 
    new data-entries.


    Parameters: 
    - csv-file (UploadFile): csv file with runway data.

    Returns: None

    Raise:
    - HTTPException (400): file or file-data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check and decode csv-file
    csv.check_format(csv_file)

    # Get list of schemas
    dict_list = await csv.extract_data(file=csv_file)
    headers = get_table_header("runways")

    # Check all aerodrome codes are valid
    a = models.Aerodrome
    v = models.VfrWaypoint

    aerodrome_codes = {r[headers["aerodrome"]].strip().upper()
                       for r in dict_list}
    aerodrome_objects = db.query(a, v)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id)\
        .filter(and_(a.vfr_waypoint.isnot(None), v.code.in_(aerodrome_codes)))\
        .all()

    aerodrome_ids_in_db = {v.code: v.waypoint_id for _, v in aerodrome_objects}

    if not len(aerodrome_codes) == len(set(aerodrome_ids_in_db.keys())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some of the aerodromes are not in the database."
        )

    try:
        data_list = [schemas.RunwayData(
            aerodrome_id=aerodrome_ids_in_db[r[headers["aerodrome"]].strip(
            ).upper()],
            number=r[headers["number"]],
            position=None if not r[headers["position"]] or r[headers["position"]].isspace(
            ) else r[headers["position"]],
            length_ft=r[headers["length_ft"]],
            surface_id=r[headers["surface_id"]]
        ) for r in dict_list]
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.errors()
        )

    # Check there are no repeated runways
    if not runways_are_unique(data_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There are repeated runway in your list, please make sure all runways are unique."
        )

    # Check all surface ids are valid
    surface_ids = {r.surface_id for r in data_list}
    surfaces_in_db = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.id.in_(surface_ids)).all()
    if not len(surface_ids) == len(surfaces_in_db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some of the surface IDs are not valid."
        )

    # Delete Runways
    deleted = db.query(models.Runway).filter(models.Runway.aerodrome_id.in_(
        list(aerodrome_ids_in_db.values()))).delete(synchronize_session=False)

    # Add data
    for runway in data_list:
        new_runway = models.Runway(
            aerodrome_id=runway.aerodrome_id,
            number=runway.number,
            position=runway.position,
            length_ft=runway.length_ft,
            surface_id=runway.surface_id
        )
        db.add(new_runway)

    db.commit()


@router.post(
    "/surface",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.RunwaySurfaceReturn
)
async def post_runway_surface(
    surface_data: schemas.RunwaySurfaceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Runway Surface Endpoint.

    Parameters: 
    - surface_data (dict): the runway surface object to be added.

    Returns: 
    Dic: dictionary with the runway surface data.

    Raise:
    - HTTPException (400): if runway surface already exists.
    - HTTPException (500): if there is a server error. 
    """

    surface_exists = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.surface == surface_data.surface).first()

    if surface_exists:
        msg = f"{surface_data.surface} is already in the database, please enter a different surface, or edit the existing one."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    new_surface = models.RunwaySurface(
        surface=surface_data.surface
    )
    db.add(new_surface)
    db.commit()
    db.refresh(new_surface)

    return new_surface


@router.put("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.RunwayReturn)
async def edit_runway(
    id: int,
    runway_data: schemas.RunwayDataEdit,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Runway Endpoint.

    Parameters: 
    - runway_data (dict): the runway  object to be added.

    Returns: 
    Dic: dictionary with the runway  data.

    Raise:
    - HTTPException (400): if runway already exists.
    - HTTPException (500): if there is a server error. 
    """
    # Check if runway exists
    runway_query = db.query(models.Runway).filter(models.Runway.id == id)
    if not runway_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid runway ID."
        )

    # Check if user has permission to update this aerodrome
    user_id = await get_user_id_from_email(email=current_user.email, db=db)
    aerodrome_id = runway_query.first().aerodrome_id

    no_permission_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"You do not have permission to update aerodrome with id {aerodrome_id}."
    )

    aerodrome_is_registered = db.query(models.Aerodrome.vfr_waypoint_id).filter_by(
        id=aerodrome_id).first()[0] is not None
    user_is_active_admin = current_user.is_active and current_user.is_admin

    if aerodrome_is_registered and not user_is_active_admin:
        raise no_permission_exception

    aerodrome_created_by_user = db.query(models.UserWaypoint).filter(and_(
        models.UserWaypoint.waypoint_id == aerodrome_id,
        models.UserWaypoint.creator_id == user_id
    )).first()

    if not aerodrome_is_registered and not aerodrome_created_by_user:
        raise no_permission_exception

    # Check if surface exists
    surface_exists = db.query(models.RunwaySurface).filter_by(
        id=runway_data.surface_id).first()
    if not surface_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid runway surface ID."
        )

    # Check if another runway with same data exists.
    runway_esxists = db.query(models.Runway).filter(and_(
        models.Runway.aerodrome_id == aerodrome_id,
        not_(models.Runway.id == id),
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
        "number": runway_data.number,
        "position": runway_data.position,
        "surface_id": runway_data.surface_id
    })
    db.commit()

    u = models.UserWaypoint
    v = models.VfrWaypoint
    a = models.Aerodrome
    r = models.Runway
    s = models.RunwaySurface

    runway_result = db.query(r, s.surface)\
        .filter(r.id == id)\
        .join(s, r.surface_id == s.id).first()

    aerodrome_result = db.query(a, v.code).filter(a.id == aerodrome_id)\
        .join(v, a.vfr_waypoint_id == v.waypoint_id).first() if aerodrome_is_registered else\
        db.query(a, u.code).filter(a.id == aerodrome_id)\
        .join(u, a.user_waypoint_id == u.waypoint_id).first()

    return {"aerodrome": aerodrome_result[1], **runway_result[0].__dict__, "surface": runway_result[1]}


@router.put(
    "/surface/{id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RunwaySurfaceReturn
)
async def edit_runway_surface(
    id: int,
    surface_data: schemas.RunwaySurfaceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Runway Surface Endpoint.

    Parameters: 
    - surface_data (dict): the runway surface object to be added.

    Returns: 
    Dic: dictionary with the runway surface data.

    Raise:
    - HTTPException (400): if runway surface already exists.
    - HTTPException (500): if there is a server error. 
    """
    surface_exists = db.query(models.RunwaySurface).filter(and_(
        models.RunwaySurface.surface == surface_data.surface,
        not_(models.RunwaySurface.id == id)
    )).first()

    if surface_exists:
        msg = f"{surface_data.surface} is already in the database, edit the existing record instead."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    surface_query = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == id
    )

    if not surface_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The surface ID provided does not exist in the database."
        )

    surface_query.update(surface_data.model_dump())
    db.commit()

    new_surface = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == id
    ).first()

    return new_surface


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_runways(
    ids: List[int],
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Runways.

    Parameters: 
    ids (List[int]): list of runway ids to be deleted.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): passenger profile not found.
    - HTTPException (500): if there is a server error. 
    """

    # Check if runway exists
    db_runway_ids = {r.id for r in db.query(
        models.Runway).filter(models.Runway.id.in_(ids)).all()}

    if not all(id in db_runway_ids for id in ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not all the Runways you're trying to delete are in the database."
        )

    # Define some variables
    user_id = await get_user_id_from_email(email=current_user.email, db=db)
    user_is_active_admin = current_user.is_active and current_user.is_admin

    # Loop thorugh ids
    for id in ids:
        # Check if user has permission to update this aerodrome
        runway_query = db.query(models.Runway).filter_by(id=id)
        aerodrome_id = runway_query.first().aerodrome_id

        no_permission_exception = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You do not have permission to update aerodrome with id {aerodrome_id}."
        )

        aerodrome_is_registered = db.query(models.Aerodrome.vfr_waypoint_id).filter_by(
            id=aerodrome_id).first()[0] is not None

        if aerodrome_is_registered and not user_is_active_admin:
            raise no_permission_exception

        aerodrome_created_by_user = db.query(models.UserWaypoint).filter(and_(
            models.UserWaypoint.waypoint_id == aerodrome_id,
            models.UserWaypoint.creator_id == user_id
        )).first()

        if not aerodrome_is_registered and not aerodrome_created_by_user:
            raise no_permission_exception

        deleted = runway_query.delete(synchronize_session=False)

        if not deleted:
            raise common_responses.internal_server_error()

    db.commit()


@router.delete("/surface/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_runway_surface(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Runway Surface.

    Parameters: 
    id (int): runway surface id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): passenger profile not found.
    - HTTPException (500): if there is a server error. 
    """

    surface_query = db.query(models.RunwaySurface).filter(
        models.RunwaySurface.id == id)

    if not surface_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The runway surface you're trying to delete is not in the database."
        )

    runway_with_surface = db.query(models.Runway).filter(
        models.Runway.surface_id == id).first()
    if runway_with_surface:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This surface cannot be deleted, as there are runways currently using it."
        )

    aircraft_performance_with_surface = db.query(models.SurfacePerformanceDecrease).\
        filter(models.SurfacePerformanceDecrease.surface_id == id).first()
    if aircraft_performance_with_surface:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This surface cannot be deleted, as there are aircraft performance tables using it."
        )

    deleted = surface_query.delete(synchronize_session=False)

    if not deleted:
        raise common_responses.internal_server_error()

    db.commit()
