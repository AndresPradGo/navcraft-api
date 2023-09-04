"""
FastAPI aircraft performance tables router

This module defines the FastAPI aircraft performance router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import csv_tools as csv
from utils.db import get_db
from utils.functions import get_table_header

router = APIRouter(tags=["Aircraft Performance Tables"])


@router.get("/takeoff-landing/csv/{profile_id}", status_code=status.HTTP_200_OK)
async def get_takeoff_landing_performance_data(
    profile_id: int,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
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
    _: schemas.TokenData = Depends(auth.validate_user)
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
        "id": performance_profile.id,
        "percent_decrease_knot_headwind": percent_decrease_knot_headwind,
        "percent_increase_knot_tailwind": percent_increase_knot_tailwind,
        "percent_increase_runway_surfaces": [{
            "surface_id": percentage.surface_id,
            "percent": percentage.percent
        } for percentage in surface_percentage_models]
    }

    return percent_adjustment_data
