"""
FastAPI aircraft performance tables router

This module defines the FastAPI aircraft performance router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import and_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.db import get_db
from utils.functions import (
    get_table_header,
    get_user_id_from_email,
    check_performance_profile_and_permissions
)

router = APIRouter(tags=["Aircraft Performance Data"])


@router.get("/takeoff-landing/csv/{profile_id}", status_code=status.HTTP_200_OK)
async def get_takeoff_landing_performance_data(
    profile_id: int,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Takeoff/Landing Performance Data Table Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - is_takeoff (bool): false if you want to get landing data.

    Returns: 
    - CSV file: csv file with the takeoff/landing data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check permissions
    performance_profile = db_session.query(
        models.PerformanceProfile).filter_by(id=profile_id).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with ID {profile_id} not found."
        )

    if performance_profile.aircraft_id is not None:
        user_id = await get_user_id_from_email(
            email=current_user.email, db_session=db_session)
        user_is_aircraft_owner = db_session.query(models.Aircraft).filter(and_(
            models.Aircraft.owner_id == user_id,
            models.Aircraft.id == performance_profile.aircraft_id
        )).first()
        if user_is_aircraft_owner is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not authorized to view this performance profile."
            )

    # Get takeoff/landing data
    if is_takeoff:
        table_data_models = db_session.query(models.TakeoffPerformance).filter(
            models.TakeoffPerformance.performance_profile_id == profile_id
        ).order_by(
            models.TakeoffPerformance.weight_lb.desc(),
            models.TakeoffPerformance.temperature_c,
            models.TakeoffPerformance.pressure_alt_ft
        ).all()
    else:
        table_data_models = db_session.query(models.LandingPerformance).filter(
            models.LandingPerformance.performance_profile_id == profile_id
        ).order_by(
            models.LandingPerformance.weight_lb.desc(),
            models.LandingPerformance.temperature_c,
            models.LandingPerformance.pressure_alt_ft
        ).all()

    # Prepare csv-file
    table_name = f"{'takeoff' if is_takeoff else 'landing'}_data"
    headers = get_table_header(table_name)

    table_data = [{
        headers["weight_lb"]: row.weight_lb,
        headers["temperature_c"]: row.temperature_c,
        headers["pressure_alt_ft"]: row.pressure_alt_ft,
        headers["groundroll_ft"]: row.groundroll_ft,
        headers["obstacle_clearance_ft"]: row.obstacle_clearance_ft
    } for row in table_data_models] if len(table_data_models) else [
        {
            headers["weight_lb"]: "",
            headers["temperature_c"]: "",
            headers["pressure_alt_ft"]: "",
            headers["groundroll_ft"]: "",
            headers["obstacle_clearance_ft"]: ""
        }
    ]

    buffer = csv.list_to_buffer(data=table_data)

    # Prepare and return response
    csv_response = StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
    )
    csv_response.headers["Content-Disposition"] = f'attachment; filename="{table_name}.csv"'

    return csv_response


@router.get(
    "/takeoff-landing-adjustments/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RunwayDistanceAdjustmentPercentages
)
async def get_takeoff_landing_adjustment_percentages(
    profile_id: int,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Runway Distance Adjustment Percentages Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - is_takeoff (bool): false if you want to get landing data.

    Returns: 
    - dict: dictionary with the runway distance adjustment percentages 
      for wind and runway surfaces.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get the performance profile
    performance_profile = db_session.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id
    )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with ID {profile_id} not found."
        )

    # Check permissions
    if performance_profile.aircraft_id is not None:
        user_id = await get_user_id_from_email(
            email=current_user.email, db_session=db_session)
        user_is_aircraft_owner = db_session.query(models.Aircraft).filter(and_(
            models.Aircraft.owner_id == user_id,
            models.Aircraft.id == performance_profile.aircraft_id
        )).first()
        if user_is_aircraft_owner is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not authorized to view this performance profile."
            )

    # Prepare Runway-Distance-Adjustment-Percetages data
    surface_percentage_models = db_session.query(models.SurfacePerformanceDecrease).filter(
        models.SurfacePerformanceDecrease.performance_profile_id == profile_id,
        models.SurfacePerformanceDecrease.is_takeoff == is_takeoff
    ).all()

    percent_decrease_knot_headwind = performance_profile.percent_decrease_takeoff_headwind_knot\
        if is_takeoff else performance_profile.percent_decrease_landing_headwind_knot
    percent_increase_knot_tailwind = performance_profile.percent_increase_takeoff_tailwind_knot\
        if is_takeoff else performance_profile.percent_increase_landing_tailwind_knot

    percent_adjustment_data = {
        "percent_decrease_knot_headwind": percent_decrease_knot_headwind,
        "percent_increase_knot_tailwind": percent_increase_knot_tailwind,
        "percent_increase_runway_surfaces": [{
            "surface_id": percentage.surface_id,
            "percent": percentage.percent
        } for percentage in surface_percentage_models]
    }

    return percent_adjustment_data


@router.post("/takeoff-landing/csv/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def manage_takeoff_landing_performance_data_with_csv_file(
    profile_id: int,
    csv_file: UploadFile,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Manage Takeoff/Landing Performance Data Endpoint.

    Usage:
    - Download the Takeoff/Landing Performance Data csv, from the 
      "Get Takeoff Landing Performance Data" endpoint.
    - Use this file to update the data in the desired way.
    - New columns can be added for your reference, but they won't be considered for updating the 
      data in the database. 
    - Do not delete or edit the headers of the existing colums in any way, 
      or the file will be rejected.
    - Enter all data in the correct colum to ensure data integrity.
    - Make sure there are no typos or repeated entries.
    - After getting a 204 response, download csv list again to check it has been uploaded correctly.

    NOTE: This endpoint will replace the current data with the new data, so upload a complete
    file, even if you just want to change 1 entry.

    Parameters: 
    - profile_id (int): id of the profile you want to update.
    - csv_file (UploadFile): csv file with takeoff/landing data.
    - is_takeoff (bool): by default, this endpoint updates takeoff 
      data. If you want to update landing data, enter false.

    Returns: None

    Raise:
    - HTTPException (400): file or file-data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check performance profile and permissions.
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )
    # Check csv-file
    csv.check_format(csv_file)

    # Get list of schemas
    table_name = f"{'takeoff' if is_takeoff else 'landing'}_data"
    headers = get_table_header(table_name)

    try:
        data_list = [schemas.TakeoffLandingPerformanceDataEntry(
            weight_lb=row[headers["weight_lb"]],
            temperature_c=row[headers["temperature_c"]],
            pressure_alt_ft=row[headers["pressure_alt_ft"]],
            groundroll_ft=row[headers["groundroll_ft"]],
            obstacle_clearance_ft=row[headers["obstacle_clearance_ft"]]
        ) for row in await csv.extract_data(file=csv_file)]
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    # Updata takeoff performance data
    if is_takeoff:
        # Delete existing takeoff performance data
        existing_takeoff_performance_data_query = db_session.query(models.TakeoffPerformance)\
            .filter_by(performance_profile_id=profile_id)
        if existing_takeoff_performance_data_query.first() is not None:
            deleted = existing_takeoff_performance_data_query.delete(
                synchronize_session='evaluate')
            if not deleted:
                raise common_responses.internal_server_error()

        # Create new takeoff performance data models
        table_data = [models.TakeoffPerformance(
            performance_profile_id=profile_id,
            weight_lb=row.weight_lb,
            temperature_c=row.temperature_c,
            pressure_alt_ft=row.pressure_alt_ft,
            groundroll_ft=row.groundroll_ft,
            obstacle_clearance_ft=row.obstacle_clearance_ft
        ) for row in data_list]

    # Updata landing performance data
    else:
        # Delete existing landing performance data
        existing_landing_performance_data_query = db_session.query(models.LandingPerformance)\
            .filter_by(performance_profile_id=profile_id)
        if existing_landing_performance_data_query.first() is not None:
            deleted = existing_landing_performance_data_query.delete(
                synchronize_session='evaluate')
            if not deleted:
                raise common_responses.internal_server_error()

        # Create new landing performance data models
        table_data = [models.LandingPerformance(
            performance_profile_id=profile_id,
            weight_lb=row.weight_lb,
            temperature_c=row.temperature_c,
            pressure_alt_ft=row.pressure_alt_ft,
            groundroll_ft=row.groundroll_ft,
            obstacle_clearance_ft=row.obstacle_clearance_ft
        ) for row in data_list]

    db_session.add_all(table_data)
    db_session.commit()


@router.put("/takeoff-landing-adjustments/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_takeoff_landing_adjustment_percentages(
    profile_id: int,
    adjustment_data: schemas.RunwayDistanceAdjustmentPercentages,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Runway Distance Adjustment Percentages Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - adjustment_data (Dict): dictionary with the percentage adjustment data.
    - is_takeoff (bool): false if you want to get landing data.

    Returns: 
    - dict: dictionary with the runway distance adjustment percentages 
      for wind and runway surfaces.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check performance profile and permissions.
    performance_profile_query = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )

    # Check runway surface data
    list_surface_ids = [
        row.surface_id for row in adjustment_data.percent_increase_runway_surfaces]
    set_surface_ids = {id for id in list_surface_ids}
    surfaces_are_unique = len(list_surface_ids) == len(set_surface_ids)
    if not surfaces_are_unique:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide only one adjustment percentage per runway surface."
        )
    list_surfaces_in_db = db_session.query(models.RunwaySurface).filter(
        models.RunwaySurface.id.in_(list_surface_ids)).all()

    all_surface_ids_in_database = len(
        list_surfaces_in_db) == len(list_surface_ids)
    if not all_surface_ids_in_database:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide valid surface ids."
        )

    # Update runway-surface adjustment data
    # Delete existing runway-surface adjustment data
    existing_surface_adjustment_data_query = db_session.query(models.SurfacePerformanceDecrease)\
        .filter(and_(
            models.SurfacePerformanceDecrease.performance_profile_id == profile_id,
            models.SurfacePerformanceDecrease.is_takeoff == is_takeoff
        ))
    if existing_surface_adjustment_data_query.first() is not None:
        deleted = existing_surface_adjustment_data_query.delete(
            synchronize_session='evaluate')
        if not deleted:
            raise common_responses.internal_server_error()

    # Add new runway-surface adjustment data
    surface_adjustment_data = [models.SurfacePerformanceDecrease(
        performance_profile_id=profile_id,
        is_takeoff=is_takeoff,
        surface_id=row.surface_id,
        percent=row.percent
    ) for row in adjustment_data.percent_increase_runway_surfaces]
    db_session.add_all(surface_adjustment_data)

    # Update wind adjustments
    if is_takeoff:
        performance_profile_query.update({
            "percent_decrease_takeoff_headwind_knot": adjustment_data.percent_decrease_knot_headwind,
            "percent_increase_takeoff_tailwind_knot": adjustment_data.percent_increase_knot_tailwind
        })
    else:
        performance_profile_query.update({
            "percent_decrease_landing_headwind_knot": adjustment_data.percent_decrease_knot_headwind,
            "percent_increase_landing_tailwind_knot": adjustment_data.percent_increase_knot_tailwind
        })

    db_session.commit()
