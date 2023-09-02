"""
FastAPI aircraft router

This module defines the FastAPI runways router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile
from sqlalchemy import and_, or_, not_, func
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses, csv_tools as csv
from utils.db import get_db

router = APIRouter(tags=["Aircraft Models"])


@router.get("/fuel-type", status_code=status.HTTP_200_OK, response_model=List[schemas.FuelTypeReturn])
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


@router.get("/make", status_code=status.HTTP_200_OK, response_model=List[schemas.AircraftMakeReturn])
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


@router.post("/fuel-type", status_code=status.HTTP_201_CREATED, response_model=schemas.FuelTypeReturn)
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


@router.post("/make", status_code=status.HTTP_201_CREATED, response_model=schemas.AircraftMakeReturn)
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


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.AircraftModelOfficialPostReturn)
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


@router.post("/performance/{model_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.PerformanceProfilePostReturn)
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


@router.post("/performance/baggage-compartment/{profile_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.BaggageCompartmentReturn)
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
            not_(models.PerformanceProfile.model_id == None),
            models.PerformanceProfile.aircraft_id == None
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


@router.post("/performance/seat-row/{profile_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.SeatRowReturn)
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
            not_(models.PerformanceProfile.model_id == None),
            models.PerformanceProfile.aircraft_id == None
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


@router.put("/fuel-type/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.FuelTypeReturn)
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


@router.put("/make/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.AircraftMakeReturn)
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


@router.put("/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.AircraftModelOfficialBaseReturn)
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


@router.put("/performance/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.PerformanceProfilePostReturn)
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
            not_(models.PerformanceProfile.model_id == None),
            models.PerformanceProfile.aircraft_id == None
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


@router.put("/performance/wheight/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.PerformanceProfilePostReturn)
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
            not_(models.PerformanceProfile.model_id == None),
            models.PerformanceProfile.aircraft_id == None
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
