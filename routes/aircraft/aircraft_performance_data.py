"""
FastAPI aircraft performance tables router

This module defines the FastAPI aircraft performance router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.config import get_table_header
from utils.db import get_db
from functions.data_processing import (
    get_user_id_from_email,
    check_performance_profile_and_permissions,
    check_completeness_and_make_preferred_if_complete
)

router = APIRouter(tags=["Aircraft Performance Data"])


@router.get("/takeoff-landing/csv/{profile_id}", status_code=status.HTTP_200_OK)
async def get_takeoff_landing_performance_csv_file(
    profile_id: int,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Takeoff/Landing Performance CSV File Endpoint.

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
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    )

    # Get takeoff/landing data
    if is_takeoff:
        table_data_models = db_session.query(models.TakeoffPerformance).filter(
            models.TakeoffPerformance.performance_profile_id == profile_id
        ).order_by(
            models.TakeoffPerformance.weight_lb.desc(),
            models.TakeoffPerformance.pressure_alt_ft,
            models.TakeoffPerformance.temperature_c
        ).all()
    else:
        table_data_models = db_session.query(models.LandingPerformance).filter(
            models.LandingPerformance.performance_profile_id == profile_id
        ).order_by(
            models.LandingPerformance.weight_lb.desc(),
            models.LandingPerformance.pressure_alt_ft,
            models.LandingPerformance.temperature_c
        ).all()

    # Prepare csv-file
    table_name = f"{'takeoff' if is_takeoff else 'landing'}_data"
    headers = get_table_header(table_name)

    table_data = [{
        headers["weight_lb"]: row.weight_lb,
        headers["pressure_alt_ft"]: row.pressure_alt_ft,
        headers["temperature_c"]: row.temperature_c,
        headers["groundroll_ft"]: row.groundroll_ft,
        headers["obstacle_clearance_ft"]: row.obstacle_clearance_ft
    } for row in table_data_models] if len(table_data_models) else [
        {
            headers["weight_lb"]: "",
            headers["pressure_alt_ft"]: "",
            headers["temperature_c"]: "",
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


@router.get("/climb/csv/{profile_id}", status_code=status.HTTP_200_OK)
async def get_climb_performance_csv_file(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Climb Performance CSV File Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.

    Returns: 
    - CSV file: csv file with the climb data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check permissions
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    )

    # Get climb data
    table_data_models = db_session.query(models.ClimbPerformance).filter(
        models.ClimbPerformance.performance_profile_id == profile_id
    ).order_by(
        models.ClimbPerformance.weight_lb.desc(),
        models.ClimbPerformance.pressure_alt_ft,
        desc(models.ClimbPerformance.temperature_c)
    ).all()

    # Prepare csv-file
    table_name = "climb_data"
    headers = get_table_header(table_name)

    table_data = [{
        headers["weight_lb"]: row.weight_lb,
        headers["pressure_alt_ft"]: row.pressure_alt_ft,
        headers["temperature_c"]: row.temperature_c,
        headers["kias"]: row.kias,
        headers["fpm"]: row.fpm,
        headers["time_min"]: row.time_min,
        headers["fuel_gal"]: row.fuel_gal,
        headers["distance_nm"]: row.distance_nm
    } for row in table_data_models] if len(table_data_models) else [
        {
            headers["weight_lb"]: "",
            headers["pressure_alt_ft"]: "",
            headers["temperature_c"]: "",
            headers["kias"]: "",
            headers["fpm"]: "",
            headers["time_min"]: "",
            headers["fuel_gal"]: "",
            headers["distance_nm"]: ""
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


@router.get("/cruise/csv/{profile_id}", status_code=status.HTTP_200_OK)
async def get_cruise_performance_csv_file(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Cruise Performance CSV File Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.

    Returns: 
    - CSV file: csv file with the climb data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check permissions
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    )

    # Get cruise data
    table_data_models = db_session.query(models.CruisePerformance).filter(
        models.CruisePerformance.performance_profile_id == profile_id
    ).order_by(
        models.CruisePerformance.weight_lb.desc(),
        models.CruisePerformance.pressure_alt_ft,
        models.CruisePerformance.temperature_c,
        models.CruisePerformance.rpm.desc()
    ).all()

    # Prepare csv-file
    table_name = "cruise_data"
    headers = get_table_header(table_name)

    table_data = [{
        headers["weight_lb"]: row.weight_lb,
        headers["pressure_alt_ft"]: row.pressure_alt_ft,
        headers["temperature_c"]: row.temperature_c,
        headers["rpm"]: row.rpm,
        headers["bhp_percent"]: row.bhp_percent,
        headers["ktas"]: row.ktas,
        headers["gph"]: row.gph
    } for row in table_data_models] if len(table_data_models) else [
        {
            headers["weight_lb"]: "",
            headers["pressure_alt_ft"]: "",
            headers["temperature_c"]: "",
            headers["rpm"]: "",
            headers["bhp_percent"]: "",
            headers["ktas"]: "",
            headers["gph"]: ""
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
    "/takeoff-landing/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.TakeoffLandingPerformanceReturn
)
async def get_takeoff_landing_performance_data(
    profile_id: int,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Takeoff/Landing Performance Data Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - is_takeoff (bool): false if you want to get landing data.

    Returns: 
    - dict: dictionary with the runway performance data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get the performance profile and check permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    ).first()

    # Get takeoff/landing data
    if is_takeoff:
        performance_data_models = db_session.query(models.TakeoffPerformance).filter(
            models.TakeoffPerformance.performance_profile_id == profile_id
        ).order_by(
            models.TakeoffPerformance.weight_lb.desc(),
            models.TakeoffPerformance.pressure_alt_ft,
            models.TakeoffPerformance.temperature_c
        ).all()
    else:
        performance_data_models = db_session.query(models.LandingPerformance).filter(
            models.LandingPerformance.performance_profile_id == profile_id
        ).order_by(
            models.LandingPerformance.weight_lb.desc(),
            models.LandingPerformance.pressure_alt_ft,
            models.LandingPerformance.temperature_c
        ).all()

    # Get Runway-Distance-Adjustment-Percetages data
    surface_percentage_models = db_session.query(models.SurfacePerformanceDecrease).filter(
        models.SurfacePerformanceDecrease.performance_profile_id == profile_id,
        models.SurfacePerformanceDecrease.is_takeoff == is_takeoff
    ).all()

    percent_decrease_knot_headwind = performance_profile.percent_decrease_takeoff_headwind_knot\
        if is_takeoff else performance_profile.percent_decrease_landing_headwind_knot
    percent_increase_knot_tailwind = performance_profile.percent_increase_takeoff_tailwind_knot\
        if is_takeoff else performance_profile.percent_increase_landing_tailwind_knot

    # Return performance data
    perfromance_data = {
        "percent_decrease_knot_headwind": percent_decrease_knot_headwind,
        "percent_increase_knot_tailwind": percent_increase_knot_tailwind,
        "percent_increase_runway_surfaces": [{
            "surface_id": percentage.surface_id,
            "percent": percentage.percent
        } for percentage in surface_percentage_models],
        "performance_data": [{
            "weight_lb": row.weight_lb,
            "pressure_alt_ft": row.pressure_alt_ft,
            "temperature_c": row.temperature_c,
            "groundroll_ft": row.groundroll_ft,
            "obstacle_clearance_ft": row.obstacle_clearance_ft
        } for row in performance_data_models] if len(performance_data_models) else [
            {
                "weight_lb": 0,
                "pressure_alt_ft": 0,
                "temperature_c": 0,
                "groundroll_ft": 0,
                "obstacle_clearance_ft": 0
            }
        ]
    }

    return perfromance_data


@router.get(
    "/climb/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ClimbPerformanceReturn
)
async def get_climb_performance_data(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Climb Performance Data Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.

    Returns: 
    - dict: dictionary with the climb performance data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get the performance profile and check permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    ).first()

    # Get climb performance data
    performance_data_models = db_session.query(models.ClimbPerformance).filter(
        models.ClimbPerformance.performance_profile_id == profile_id
    ).order_by(
        models.ClimbPerformance.weight_lb.desc(),
        models.ClimbPerformance.pressure_alt_ft,
        desc(models.ClimbPerformance.temperature_c)
    ).all()

    take_off_taxi_fuel_gallons = performance_profile.take_off_taxi_fuel_gallons
    percent_increase_climb_temperature_c = performance_profile.percent_increase_climb_temperature_c

    # Return climb performance data
    perfromance_data = {
        "take_off_taxi_fuel_gallons": take_off_taxi_fuel_gallons,
        "percent_increase_climb_temperature_c": percent_increase_climb_temperature_c,
        "performance_data": [{
            "weight_lb": row.weight_lb,
            "pressure_alt_ft": row.pressure_alt_ft,
            "temperature_c": row.temperature_c,
            "time_min": row.time_min,
            "fuel_gal": row.fuel_gal,
            "distance_nm": row.distance_nm,
            "kias": row.kias,
            "fpm": row.fpm
        } for row in performance_data_models] if len(performance_data_models) else [
            {
                "weight_lb": 0,
                "pressure_alt_ft": 0,
                "temperature_c": 0,
                "time_min": 0,
                "fuel_gal": 0,
                "distance_nm": 0,
                "kias": 0,
                "fpm": 0
            }
        ]
    }

    return perfromance_data


@router.get(
    "/cruise/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.CruisePerformanceReturn
)
async def get_cruise_performance_data(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Cruise Performance Data Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.

    Returns: 
    - dict: dictionary with the cruise performance data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get the performance profile and check permissions.
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=await get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    )

    # Get cruise performance data
    performance_data_models = db_session.query(models.CruisePerformance).filter(
        models.CruisePerformance.performance_profile_id == profile_id
    ).order_by(
        models.CruisePerformance.weight_lb.desc(),
        models.CruisePerformance.pressure_alt_ft,
        models.CruisePerformance.temperature_c,
        models.CruisePerformance.rpm.desc()
    ).all()

    # Return cruise performance data
    perfromance_data = {
        "performance_data": [{
            "weight_lb": row.weight_lb,
            "pressure_alt_ft": row.pressure_alt_ft,
            "temperature_c": row.temperature_c,
            "rpm": row.rpm,
            "bhp_percent": row.bhp_percent,
            "ktas": row.ktas,
            "gph": row.gph
        } for row in performance_data_models] if len(performance_data_models) else [
            {
                "weight_lb": 0,
                "pressure_alt_ft": 0,
                "temperature_c": 0,
                "rpm": 0,
                "bhp_percent": 0,
                "ktas": 0,
                "gph": 0
            }
        ]
    }

    return perfromance_data


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
            weight_lb=float(row[headers["weight_lb"]]),
            temperature_c=float(row[headers["temperature_c"]]),
            pressure_alt_ft=float(row[headers["pressure_alt_ft"]]),
            groundroll_ft=float(row[headers["groundroll_ft"]]),
            obstacle_clearance_ft=float(row[headers["obstacle_clearance_ft"]])
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

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )


@router.post("/climb/csv/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def manage_climb_performance_data_with_csv_file(
    profile_id: int,
    csv_file: UploadFile,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Manage climb Performance Data Endpoint.

    Usage:
    - Download the climb Performance Data csv, from the 
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
    - csv_file (UploadFile): csv file with climb data.
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
    table_name = "climb_data"
    headers = get_table_header(table_name)

    try:
        data_list = [schemas.ClimbPerformanceDataEntry(
            weight_lb=int(float(row[headers["weight_lb"]])),
            temperature_c=int(float(row[headers["temperature_c"]])),
            pressure_alt_ft=int(float(row[headers["pressure_alt_ft"]])),
            time_min=int(float(row[headers["time_min"]])),
            fuel_gal=row[headers["fuel_gal"]],
            distance_nm=int(float(row[headers["distance_nm"]])),
            kias=None if headers["kias"] not in row
            or not row[headers["kias"]]
            or row[headers["kias"]].isspace()
            else int(float(row[headers["kias"]])),
            fpm=None if headers["fpm"] not in row
            or not row[headers["fpm"]]
            or row[headers["fpm"]].isspace()
            else int(float(row[headers["fpm"]]))
        ) for row in await csv.extract_data(file=csv_file)]
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    # Delete existing climb performance data
    existing_climb_performance_data_query = db_session.query(models.ClimbPerformance)\
        .filter_by(performance_profile_id=profile_id)
    if existing_climb_performance_data_query.first() is not None:
        deleted = existing_climb_performance_data_query.delete(
            synchronize_session='evaluate')
        if not deleted:
            raise common_responses.internal_server_error()

    # Create new climb performance data models
    table_data = [models.ClimbPerformance(
        performance_profile_id=profile_id,
        weight_lb=row.weight_lb,
        temperature_c=row.temperature_c,
        pressure_alt_ft=row.pressure_alt_ft,
        time_min=row.time_min,
        fuel_gal=row.fuel_gal,
        distance_nm=row.distance_nm,
        kias=row.kias,
        fpm=row.fpm
    ) for row in data_list]

    db_session.add_all(table_data)
    db_session.commit()

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )


@router.post("/cruise/csv/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def manage_cruise_performance_data_with_csv_file(
    profile_id: int,
    csv_file: UploadFile,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Manage cruise Performance Data Endpoint.

    Usage:
    - Download the cruise Performance Data csv, from the 
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
    - csv_file (UploadFile): csv file with cruise data.
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
    table_name = "cruise_data"
    headers = get_table_header(table_name)

    try:
        data_list = [schemas.CruisePerformanceDataEntry(
            weight_lb=int(float(row[headers["weight_lb"]])),
            temperature_c=int(float(row[headers["temperature_c"]])),
            pressure_alt_ft=int(float(row[headers["pressure_alt_ft"]])),
            rpm=int(float(row[headers["rpm"]])),
            bhp_percent=int(float(row[headers["bhp_percent"]])),
            ktas=int(float(row[headers["ktas"]])),
            gph=row[headers["gph"]]
        ) for row in await csv.extract_data(file=csv_file)]
    except ValidationError as error:
        # pylint: disable=raise-missing-from
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors()
        )

    # Delete existing cruise performance data
    existing_cruise_performance_data_query = db_session.query(models.CruisePerformance)\
        .filter_by(performance_profile_id=profile_id)
    if existing_cruise_performance_data_query.first() is not None:
        deleted = existing_cruise_performance_data_query.delete(
            synchronize_session='evaluate')
        if not deleted:
            raise common_responses.internal_server_error()

    # Create new cruise performance data models
    table_data = [models.CruisePerformance(
        performance_profile_id=profile_id,
        weight_lb=row.weight_lb,
        temperature_c=row.temperature_c,
        pressure_alt_ft=row.pressure_alt_ft,
        rpm=row.rpm,
        bhp_percent=row.bhp_percent,
        ktas=row.ktas,
        gph=row.gph
    ) for row in data_list]

    db_session.add_all(table_data)
    db_session.commit()

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )


@router.put("/takeoff-landing-adjustments/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_takeoff_landing_adjustment_values(
    profile_id: int,
    adjustment_data: schemas.RunwayDistanceAdjustmentPercentages,
    is_takeoff: bool = True,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Takeoff/Landing Performance Adjustment Values Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - adjustment_data (Dict): dictionary with the percentage adjustment data.
    - is_takeoff (bool): false if you want to get landing data.

    Returns: None

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


@router.put("/climb-adjustments/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_climb_performance_adjustment_values(
    profile_id: int,
    adjustment_data: schemas.ClimbPerformanceAdjustments,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Climb Performance Adjustment Values Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - adjustment_data (Dict): dictionary with the percentage adjustment data.

    Returns: None

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

    # Update climb performance adjustment values
    performance_profile_query.update({
        "take_off_taxi_fuel_gallons": adjustment_data.take_off_taxi_fuel_gallons,
        "percent_increase_climb_temperature_c": adjustment_data.percent_increase_climb_temperature_c
    })

    db_session.commit()
