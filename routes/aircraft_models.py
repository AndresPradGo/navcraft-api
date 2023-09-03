"""
FastAPI aircraft router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, or_, not_, func
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.db import get_db
from utils.functions import get_table_header

router = APIRouter(tags=["Aircraft Models"])


@router.get("/takeoff-landing-performance/csv-table/{profile_id}", status_code=status.HTTP_200_OK)
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


@router.get(
    "/fuel-type",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.FuelTypeReturn]
)
async def get_fuel_types(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Fuel Types Endpoint.

    Parameters: 
    - id (int): fuel type id, for returning only 1 fuel type. If 0 or none, 
      it returns all entries. If id doesn't exist, it returns an empty list

    Returns: 
    - List: list of dictionaries with the fuel types.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    fuel_types = db.query(models.FuelType).filter(or_(
        not_(id),
        models.FuelType.id == id
    )).all()

    return [fuel_type.__dict__ for fuel_type in fuel_types]


@router.get(
    "/make",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.AircraftMakeReturn]
)
async def get_aircraft_manufacturers(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Aircraft Manufacturers Endpoint.

    Parameters: 
    - id (int): fuel type id, for returning only 1 manufacturer. If 0 or none, 
      it returns all entries. If id doesn't exist, it returns an empty list

    Returns: 
    - List: list of dictionaries with the manufacturers' data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    manufacturers = db.query(models.AircraftMake).filter(or_(
        not_(id),
        models.AircraftMake.id == id
    )).all()

    return [manufacturer.__dict__ for manufacturer in manufacturers]


@router.post(
    "/fuel-type",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTypeReturn
)
async def post_new_fuel_type(
    fuel_type: schemas.FuelTypeData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Fuel Type Endpoint.

    Parameters: 
    - fuel_type (dict): the fuel type data to be added.

    Returns: 
    - Dic: dictionary with the fuel type data added to the database, and the id.

    Raise:
    - HTTPException (400): if fuel type already exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if fuel type already exists in database
    fuelt_type_exists = db.query(models.FuelType).filter_by(
        name=fuel_type.name).first()
    if fuelt_type_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{fuel_type.name} fuel already exists in the database."
        )
    # Add fuel type to database
    new_fuel_type = models.FuelType(**fuel_type.model_dump())
    db.add(new_fuel_type)
    db.commit()

    # Return fuel type data
    db.refresh(new_fuel_type)

    return new_fuel_type


@router.post(
    "/make",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftMakeReturn
)
async def post_new_aircraft_manufacturer(
    make_data: schemas.AircraftMakeData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post Aircraft Manufacturer Endpoint.

    Parameters: 
    - make_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if manufacturer already exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if manufacturer already exists in database
    make_exists = db.query(models.AircraftMake).filter_by(
        name=make_data.name).first()
    if make_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{make_data.name} already exists in the database."
        )
    # Add manufacturer to database
    new_make = models.AircraftMake(**make_data.model_dump())
    db.add(new_make)
    db.commit()

    # Return manufacturer data
    db.refresh(new_make)
    return new_make


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftModelOfficialPostReturn
)
async def post_new_aircraft_model(
    model_data: schemas.AircraftModelOfficialPostData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Aircraft Model Endpoint.

    Parameters: 
    - model_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if model already exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if model already exists in database
    model_exists = db.query(models.AircraftModel).filter(
        func.upper(models.AircraftModel.model) == func.upper(model_data.model)).first()
    if model_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{model_data.model} already exists in the database."
        )

    # Check manufacturer exists
    make_id_exists = db.query(models.AircraftMake).filter_by(
        id=model_data.make_id).first()
    if not make_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer ID {model_data.make_id} doesn't exist."
        )

    # Check fuel type exists
    fuel_type_id_exists = db.query(models.FuelType).filter_by(
        id=model_data.fuel_type_id).first()
    if not fuel_type_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type ID {model_data.fuel_type_id} doesn't exist."
        )

    # Post aircraft model
    new_model = models.AircraftModel(
        model=model_data.model,
        code=model_data.code,
        make_id=model_data.make_id,
    )
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    new_model_dict = {**new_model.__dict__}

    # Post performance profile
    new_performance_profile = models.PerformanceProfile(
        model_id=new_model.id,
        fuel_type_id=model_data.fuel_type_id,
        name=model_data.performance_profile_name,
        is_complete=model_data.is_complete
    )
    db.add(new_performance_profile)
    db.commit()
    db.refresh(new_performance_profile)

    return {
        **new_model_dict,
        "fuel_type_id": new_performance_profile.fuel_type_id,
        "performance_profile_name": new_performance_profile.name,
        "performance_profile_id": new_performance_profile.id,
        "is_complete": new_performance_profile.is_complete
    }


@router.post(
    "/performance/{model_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfilePostReturn
)
async def post_new_aircraft_model_performance_profile(
    model_id: int,
    performance_data: schemas.PerformanceProfilePostData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Model Performance Profile Endpoint.

    Parameters: 
    - model_id (int): model id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if model doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check model exists
    model = db.query(models.AircraftModel).filter_by(id=model_id).first()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with id {model_id} doesn't exist."
        )

    # Check profile is not repeated
    profile_exists = db.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.model_id == model_id,
        models.PerformanceProfile.name == performance_data.performance_profile_name
    )).first()
    if profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance Profile {performance_data.performance_profile_name} already exists."
        )

    # Check fuel type exists
    fuel_type_id_exists = db.query(models.FuelType).filter_by(
        id=performance_data.fuel_type_id).first()
    if not fuel_type_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type ID {performance_data.fuel_type_id} doesn't exist."
        )

    # Post profile
    new_performance_profile = models.PerformanceProfile(
        model_id=model_id,
        fuel_type_id=performance_data.fuel_type_id,
        name=performance_data.performance_profile_name,
        is_complete=performance_data.is_complete
    )
    db.add(new_performance_profile)
    db.commit()

    # Return profile
    db.refresh(new_performance_profile)
    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name
    }


@router.post(
    "/performance/baggage-compartment/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
async def post_new_baggage_compartment(
    profile_id: int,
    data: schemas.BaggageCompartmentData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Baggage Compartment Endpoint.

    Parameters: 
    - profile_id (int): profile id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if performance profile exists
    performance_profile = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} doesn't exist."
        )
    # Check baggage compartment name is not repeated
    baggage_compartment_exists = db.query(models.BaggageCompartment).filter(and_(
        models.BaggageCompartment.name == data.name,
        models.BaggageCompartment.performance_profile_id == profile_id
    )).first()
    if baggage_compartment_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment {data.name} for profile with id {profile_id}, already exists."
        )

    # Post baggage compartment
    new_baggage_compartment = models.BaggageCompartment(
        performance_profile_id=profile_id,
        name=data.name,
        arm_in=data.arm_in,
        weight_limit_lb=data.weight_limit_lb
    )

    db.add(new_baggage_compartment)
    db.commit()
    db.refresh(new_baggage_compartment)

    return new_baggage_compartment.__dict__


@router.post(
    "/performance/seat-row/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.SeatRowReturn,
)
async def post_new_seat_row(
    profile_id: int,
    data: schemas.SeatRowData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Seat Row Endpoint.

    Parameters: 
    - profile_id (int): profile id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if performance profile exists
    performance_profile = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {profile_id} doesn't exist."
        )
    # Check seat row name is not repeated
    seat_row_exists = db.query(models.SeatRow).filter(and_(
        models.SeatRow.name == data.name,
        models.SeatRow.performance_profile_id == profile_id
    )).first()
    if seat_row_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row {data.name} for profile with id {profile_id}, already exists."
        )

    # Post baggage compartment
    new_seat_row = models.SeatRow(
        performance_profile_id=profile_id,
        name=data.name,
        arm_in=data.arm_in,
        weight_limit_lb=data.weight_limit_lb,
        number_of_seats=data.number_of_seats
    )

    db.add(new_seat_row)
    db.commit()
    db.refresh(new_seat_row)

    return new_seat_row.__dict__


@router.post(
    "/performance/weight-balance/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
async def post_new_weight_and_balance_profile(
    profile_id: int,
    data: schemas.WeightBalanceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Post New Weight And Balance Profile Endpoint.

    Parameters: 
    - profile_id (int): profile id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check performance profile exists
    performance_profile = db.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == profile_id,
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.model_id.isnot(None)
    )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model performance profile with ID {profile_id} was not found."
        )

    # Check weight and balance profile doesn't already exist
    wb_profile_exists = db.query(
        models.WeightBalanceProfile).filter_by(name=data.name).first()
    if wb_profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weight and Balance profile {data.name} already exists for performance profile with ID {profile_id}."
        )

    # Post weight and balance profile
    new_profile = models.WeightBalanceProfile(
        performance_profile_id=profile_id,
        name=data.name,
        max_take_off_weight_lb=data.max_take_off_weight_lb
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    # Post weight and balance limits
    wb_profile_id = new_profile.id
    new_limits = [models.WeightBalanceLimit(
        weight_balance_profile_id=wb_profile_id,
        from_cg_in=limit.from_cg_in,
        from_weight_lb=limit.from_weight_lb,
        to_cg_in=limit.to_cg_in,
        to_weight_lb=limit.to_weight_lb,
    ) for limit in data.limits]

    db.add_all(new_limits)
    db.commit()

    # Return weight and balance profile
    weight_balance_profile = db.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id).first()
    limits = db.query(models.WeightBalanceLimit).filter_by(
        weight_balance_profile_id=wb_profile_id).all()

    return {
        **weight_balance_profile.__dict__,
        "limits": [limit.__dict__ for limit in limits]
    }


@router.put(
    "/fuel-type/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.FuelTypeReturn
)
async def edit_fuel_type(
    id: int,
    fuel_type: schemas.FuelTypeData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Fuel Type Endpoint.

    Parameters: 
    - id (int): fuel type id.
    - fuel_type (dict): the fuel type data to be added.

    Returns: 
    - Dic: dictionary with the new fuel type data.

    Raise:
    - HTTPException (400): if fuel type doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check id is valid
    fuelt_type_query = db.query(models.FuelType).filter(
        models.FuelType.id == id)

    if not fuelt_type_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type with id {id} doesn't exists in the database."
        )

    # Check if fuel type with same name exists
    fuelt_type_exists = db.query(models.FuelType).filter(and_(
        models.FuelType.name == fuel_type.name,
        not_(models.FuelType.id == id)
    )).first()
    if fuelt_type_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{fuel_type.name} fuel already exists in the database."
        )
    # Edit fuel type
    fuelt_type_query.update(fuel_type.model_dump())
    db.commit()

    # Return fuel type data
    return fuelt_type_query.first().__dict__


@router.put(
    "/make/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftMakeReturn
)
async def edit_aircraft_manufacturer(
    id: int,
    make_data: schemas.AircraftMakeData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Aircraft Manufacturer Endpoint.

    Parameters: 
    - id (int): Aircraft Manufacturer id.
    - make_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the new manufacturer data.

    Raise:
    - HTTPException (400): if manufacturer id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check id is valid
    make_query = db.query(models.AircraftMake).filter(
        models.AircraftMake.id == id)

    if not make_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer with id {id} doesn't exists in the database."
        )

    # Check if manufacturer with same name exists
    make_exists = db.query(models.AircraftMake).filter(and_(
        models.AircraftMake.name == make_data.name,
        not_(models.AircraftMake.id == id)
    )).first()
    if make_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{make_data.name} already exists in the database."
        )
    # Edit manufacturer
    make_query.update(make_data.model_dump())
    db.commit()

    # Return manufacturer data
    return make_query.first().__dict__


@router.put(
    "/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AircraftModelOfficialBaseReturn
)
async def edit_aircraft_model(
    id: int,
    model_data: schemas.AircraftModelOfficialBaseData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Aircraft Model Endpoint.

    Parameters: 
    - id (int): model id
    - model_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if model doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if model exists
    model_query = db.query(models.AircraftModel).filter_by(id=id)
    if model_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with id {id} doesn't exist."
        )

    # Check if new model data is repeated in
    model_exists = db.query(models.AircraftModel).filter(and_(
        not_(models.AircraftModel.id == id),
        func.upper(models.AircraftModel.model) == func.upper(model_data.model),
    )).first()
    if model_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{model_data.model} already exists in the database."
        )

    # Check manufacturer exists
    make_id_exists = db.query(models.AircraftMake).filter_by(
        id=model_data.make_id).first()
    if not make_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer ID {model_data.make_id} doesn't exist."
        )

    # Update aircraft model
    model_query.update(model_data.model_dump())
    db.commit()

    new_model = db.query(models.AircraftModel).filter_by(id=id).first()
    return {**new_model.__dict__}


@router.put(
    "/performance/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfilePostReturn
)
async def edit_aircraft_model_performance_profile(
    id: int,
    performance_data: schemas.PerformanceProfilePostData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Model Performance Profile Endpoint.

    Parameters: 
    - id (int): performance profile id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if performance profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check profile exists
    performance_profile_query = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        ))
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {id} doesn't exist."
        )

    # Check profile is not repeated
    profile_exists = db.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.model_id == performance_profile_query.first().model_id,
        models.PerformanceProfile.name == performance_data.performance_profile_name
    )).first()
    if profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance Profile {performance_data.performance_profile_name} already exists."
        )

    # Check fuel type exists
    fuel_type_id_exists = db.query(models.FuelType).filter_by(
        id=performance_data.fuel_type_id).first()
    if not fuel_type_id_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type ID {performance_data.fuel_type_id} doesn't exist."
        )

    # Update profile
    performance_profile_query.update({
        "name": performance_data.performance_profile_name,
        "fuel_type_id": performance_data.fuel_type_id,
        "is_complete": performance_data.is_complete
    })
    db.commit()

    new_performance_profile = db.query(
        models.PerformanceProfile).filter_by(id=id).first()
    return {**new_performance_profile.__dict__, "performance_profile_name": new_performance_profile.name}


@router.put(
    "/performance/wheight/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfilePostReturn
)
async def edit_weight_and_balance_data_for_aircraft_model_performance_profile(
    id: int,
    performance_data: schemas.PerformanceProfileWightBalanceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit  Weight And Balance Data For Model Performance Profile Endpoint.

    Parameters: 
    - id (int): performance profile id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the performance profile data, and the id.

    Raise:
    - HTTPException (400): if performance profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check profile exists
    performance_profile_query = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        ))
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with id {id} doesn't exist."
        )
    # Update profile
    performance_profile_query.update({
        "center_of_gravity_in": performance_data.center_of_gravity_in,
        "empty_weight_lb": performance_data.empty_weight_lb,
        "max_ramp_weight_lb": performance_data.max_ramp_weight_lb,
        "max_landing_weight_lb": performance_data.max_landing_weight_lb,
        "fuel_arm_in": performance_data.fuel_arm_in,
        "fuel_capacity_gallons": performance_data.fuel_capacity_gallons
    })
    db.commit()

    new_performance_profile = db.query(
        models.PerformanceProfile).filter_by(id=id).first()
    return {**new_performance_profile.__dict__, "performance_profile_name": new_performance_profile.name}


@router.put(
    "/performance/baggage-compartment/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.BaggageCompartmentReturn
)
async def edit_baggage_compartment(
    id: int,
    data: schemas.BaggageCompartmentData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Baggage Compartment Endpoint.

    Parameters: 
    - id (int): baggage compartment id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if baggage compartment doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check baggage compartment exists
    compartment_query = db.query(models.BaggageCompartment).filter_by(id=id)
    if compartment_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment with ID {id} not found."
        )

    # Check performance profile
    performance_profile = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == compartment_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The Performance profile you're trying to edit, is not for an aircraft model."
        )

    # Check baggage compartment name is not repeated
    baggage_compartment_exists = db.query(models.BaggageCompartment).filter(and_(
        models.BaggageCompartment.name == data.name,
        models.BaggageCompartment.performance_profile_id == performance_profile.id,
        not_(models.BaggageCompartment.id == id)
    )).first()
    if baggage_compartment_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment {data.name} for profile with id {performance_profile.id}, already exists."
        )

    # Edit baggage compartment
    compartment_query.update({
        "name": data.name,
        "arm_in": data.arm_in,
        "weight_limit_lb": data.weight_limit_lb
    })
    db.commit()

    return db.query(models.BaggageCompartment).filter_by(id=id).first().__dict__


@router.put(
    "/performance/seat-row/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.SeatRowReturn
)
async def edit_seat_row(
    id: int,
    data: schemas.SeatRowData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Seat Row Endpoint.

    Parameters: 
    - id (int): seat row id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if seat row doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check baggage compartment exists
    row_query = db.query(models.SeatRow).filter_by(id=id)
    if row_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row with ID {id} not found."
        )

    # Check performance profile
    performance_profile = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == row_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The Performance profile you're trying to edit, is not for an aircraft model."
        )

    # Check seat row name is not repeated
    seat_row_exists = db.query(models.SeatRow).filter(and_(
        models.SeatRow.name == data.name,
        models.SeatRow.performance_profile_id == performance_profile.id,
        not_(models.SeatRow.id == id)
    )).first()
    if seat_row_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row {data.name} for profile with id {performance_profile.id}, already exists."
        )

    # Edit seat row
    row_query.update({
        "name": data.name,
        "arm_in": data.arm_in,
        "weight_limit_lb": data.weight_limit_lb,
        "number_of_seats": data.number_of_seats
    })
    db.commit()

    return db.query(models.SeatRow).filter_by(id=id).first().__dict__


@router.put(
    "/performance/weight-balance/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
async def edit_weight_and_balance_profile(
    id: int,
    data: schemas.WeightBalanceData,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Edit Weight And Balance Profile Endpoint.

    Parameters: 
    - id (int): weight and balance id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if weight and balance doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if W&B ID exists
    wb_profile_query = db.query(models.WeightBalanceProfile).filter_by(id=id)
    if wb_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"W&B Profile with ID {id} was not found."
        )

    # Check if performance profile is for model
    performance_profile = db.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == wb_profile_query.first().performance_profile_id,
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.model_id.isnot(None)
    )).first()

    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The performance profile you are trying to edit is not for and aircraft model."
        )

    # Check weight and balance profile doesn't already exist
    wb_profile_exists = db.query(
        models.WeightBalanceProfile).filter(and_(
            models.WeightBalanceProfile.name == data.name,
            models.WeightBalanceProfile.performance_profile_id == performance_profile.id,
            not_(models.WeightBalanceProfile.id == id)
        )).first()
    if wb_profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weight and Balance profile '{data.name}' already exists for performance profile with ID {performance_profile.id}."
        )

    # Update weight and balance limts
    new_limits = [models.WeightBalanceLimit(
        weight_balance_profile_id=id,
        from_cg_in=limit.from_cg_in,
        from_weight_lb=limit.from_weight_lb,
        to_cg_in=limit.to_cg_in,
        to_weight_lb=limit.to_weight_lb
    ) for limit in data.limits]

    _ = db.query(models.WeightBalanceLimit).filter(
        models.WeightBalanceLimit.weight_balance_profile_id == id).delete()

    db.add_all(new_limits)

    # Update weight and balance profile
    wb_profile_query.update({
        "name": data.name,
        "max_take_off_weight_lb": data.max_take_off_weight_lb
    })

    db.commit()

    # Return weight and balance profile
    weight_balance_profile = db.query(
        models.WeightBalanceProfile).filter_by(id=id).first()
    limits = db.query(models.WeightBalanceLimit).filter_by(
        weight_balance_profile_id=id).all()

    return {
        **weight_balance_profile.__dict__,
        "limits": [limit.__dict__ for limit in limits]
    }


@router.delete("/fuel-type/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fuel_type(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Fuel Type Endpoint.

    Parameters: 
    - id (int): fuel type id.

    Returns: None

    Raise:
    - HTTPException (400): if fuel type doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if fuel type exists.
    fuelt_type_query = db.query(models.FuelType).filter(
        models.FuelType.id == id)
    if not fuelt_type_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel type with id {id} doesn't exists in the database."
        )

    # Delete fuel type
    deleted = fuelt_type_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db.commit()


@router.delete("/make/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aircraft_manufacturer(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Aircraft Manufaturer Endpoint.

    Parameters: 
    - id (int): manufacturer id.

    Returns: None

    Raise:
    - HTTPException (400): if manufacturer id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if manufacturer exists.
    make_query = db.query(models.AircraftMake).filter(
        models.AircraftMake.id == id)

    if not make_query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer with id {id} doesn't exists in the database."
        )

    # Delete manufacturer
    deleted = make_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db.commit()


@router.delete("/performance/baggage-compartment/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_baggage_compartment(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Baggage Compartment Endpoint.

    Parameters: 
    - id (int): baggage compartment id.

    Returns: None

    Raise:
    - HTTPException (400): if baggage compartment id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check baggage compartment exists
    compartment_query = db.query(models.BaggageCompartment).filter_by(id=id)
    if compartment_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baggage compartment with ID {id} not found."
        )

    # Check parformance profile is for an aircraft model
    performance_profile = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == compartment_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The Performance profile you're trying to edit, is not for an aircraft model."
        )

    # Delete baggage compartment
    deleted = compartment_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db.commit()


@router.delete("/performance/seat-row/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seat_row(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Seat Row Endpoint.

    Parameters: 
    - id (int): seat row id.

    Returns: None

    Raise:
    - HTTPException (400): if seat row id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check seat row exists
    row_query = db.query(models.SeatRow).filter_by(id=id)
    if row_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat row with ID {id} not found."
        )

    # Check performance profile is for an aircraft model
    performance_profile = db.query(
        models.PerformanceProfile).filter(and_(
            models.PerformanceProfile.id == row_query.first().performance_profile_id,
            models.PerformanceProfile.model_id.isnot(None),
            models.PerformanceProfile.aircraft_id.is_(None)
        )).first()
    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The Performance profile you're trying to edit, is not for an aircraft model."
        )

    # Delete seat row
    deleted = row_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()
    db.commit()


@router.delete("/performance/weight-balance/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight_and_balance_profile(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_admin_user)
):
    """
    Delete Weight and Balance Profile Endpoint.

    Parameters: 
    - id (int): weight and balance id.

    Returns: None

    Raise:
    - HTTPException (400): if W&B profile id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if W&B ID exists
    wb_profile_query = db.query(models.WeightBalanceProfile).filter_by(id=id)
    if wb_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"W&B Profile with ID {id} was not found."
        )

    # Check if performance profile is for model
    is_aircraft_model_profile = db.query(models.PerformanceProfile).filter(and_(
        models.PerformanceProfile.id == wb_profile_query.first().performance_profile_id,
        models.PerformanceProfile.aircraft_id.is_(None),
        models.PerformanceProfile.model_id.isnot(None)
    )).first()

    if is_aircraft_model_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The performance profile you are trying to edit is not for and aircraft model."
        )

    # Delete W&B Profile
    deleted = wb_profile_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()

    db.commit()
