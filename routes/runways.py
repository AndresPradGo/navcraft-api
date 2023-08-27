"""
FastAPI runways router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
from queries import user_queries
import schemas
from utils import common_responses
from utils.db import get_db

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


@router.get("/surfaces", status_code=status.HTTP_200_OK, response_model=List[schemas.RunwaySurfaceReturn])
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
    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
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


@router.post("/surface", status_code=status.HTTP_201_CREATED, response_model=schemas.RunwaySurfaceReturn)
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
    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
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


@router.put("/surface/{id}", status_code=status.HTTP_200_OK, response_model=schemas.RunwaySurfaceReturn)
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


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_runway(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Runway.

    Parameters: 
    id (int): runway id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): passenger profile not found.
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
    user_id = await user_queries.get_id_from(email=current_user.email, db=db)
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
