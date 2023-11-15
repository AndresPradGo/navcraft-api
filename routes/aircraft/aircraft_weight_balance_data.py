"""
FastAPI aircraft weight and balance router

This module defines the FastAPI aircraft weight and balance router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
import io

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse
import pytz
import matplotlib.pyplot as plt
from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import (
    check_performance_profile_and_permissions,
    get_user_id_from_email,
    check_completeness_and_make_preferred_if_complete
)

router = APIRouter(tags=["Aircraft Weight and Balance Data"])


@router.get(
    "/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GetWeightBalanceData
)
def get_aircraft_weight_balance_data(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Weight and Balance Data Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.

    Returns: 
    - dict: dictionary with the weight and balance data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get the performance profile and check permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    ).first()

    # Get weight and balance profiles
    weight_balance_profiles = db_session.query(models.WeightBalanceProfile).filter(
        models.WeightBalanceProfile.performance_profile_id == profile_id
    ).all()

    wb_profile_ids = [wb.id for wb in weight_balance_profiles]
    weight_balance_profile_limits = db_session.query(models.WeightBalanceLimit).filter(
        models.WeightBalanceLimit.weight_balance_profile_id.in_(wb_profile_ids)
    ).all()

    # Return weight and balance data
    data = {
        "center_of_gravity_in": performance_profile.center_of_gravity_in
        if performance_profile.center_of_gravity_in is not None else 0,
        "empty_weight_lb": performance_profile.empty_weight_lb
        if performance_profile.empty_weight_lb is not None else 0,
        "max_ramp_weight_lb": performance_profile.max_ramp_weight_lb
        if performance_profile.max_ramp_weight_lb is not None else 0,
        "max_takeoff_weight_lb": performance_profile.max_takeoff_weight_lb
        if performance_profile.max_takeoff_weight_lb is not None else 0,
        "max_landing_weight_lb": performance_profile.max_landing_weight_lb
        if performance_profile.max_landing_weight_lb is not None else 0,
        "baggage_allowance_lb": performance_profile.baggage_allowance_lb
        if performance_profile.baggage_allowance_lb is not None else 0,
        "weight_balance_profiles": [{
            "id": profile.id,
            "name": profile.name,
            "limits": [{
                "id": limit.id,
                "cg_location_in": limit.cg_location_in,
                "weight_lb": limit.weight_lb,
                "sequence": limit.sequence
            } for limit in weight_balance_profile_limits],
            "created_at_utc": pytz.timezone('UTC').localize(profile.created_at),
            "last_updated_utc": pytz.timezone('UTC').localize(profile.last_updated),
        } for profile in weight_balance_profiles]
    }

    return data


@router.get(
    "/graph/{profile_id}",
    status_code=status.HTTP_200_OK
)
def get_aircraft_weight_and_balance_graph(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Aircraft Weight and Balance Graph Endpoint.

    Parameters:
    - profile_id (int): aircraft performance profile id.

    Returns: 
    - Png-file: W&B graph.

    Raise:
    - HTTPException (400): if performance profile doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Get the performance profile and check permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id,
        auth_non_admin_get_model=True
    ).first()

    # Define line graph style variables
    colors = ['#00D5C8', '#D500CB', '#4AD500', '#D50000']
    line_styles = ['-', '--', '-.', ':']

    # Get weight and balance profiles
    weight_balance_profile_limits = db_session.query(
        models.WeightBalanceProfile,
        models.WeightBalanceLimit
    ).join(
        models.WeightBalanceLimit,
        models.WeightBalanceProfile.id == models.WeightBalanceLimit.weight_balance_profile_id
    ).filter(
        models.WeightBalanceProfile.performance_profile_id == profile_id
    ).order_by(
        models.WeightBalanceProfile.id,
        models.WeightBalanceLimit.sequence
    ).all()
    weight_balance_profiles_names = {
        profile.name for profile, _ in weight_balance_profile_limits}
    weight_balance_profiles = []

    for profile_name in weight_balance_profiles_names:
        weight_balance_profile = {"name": profile_name}
        cg_locations = []
        weights = []
        for profile, limit in weight_balance_profile_limits:
            if profile.name == profile_name:
                cg_locations.append(float(limit.cg_location_in))
                weights.append(float(limit.weight_lb))
        weight_balance_profile["limits"] = (cg_locations, weights)
        weight_balance_profiles.append(weight_balance_profile)

    weight_balance_profiles.sort(
        key=lambda i: max(i["limits"][1]), reverse=True)

    # Create plot limits
    plot_limits = {
        "top": float(performance_profile.max_takeoff_weight_lb),
        "right": 0,
        "bottom": float(performance_profile.max_takeoff_weight_lb),
        "left": 10000
    }
    for weight_balance_profile in weight_balance_profiles:
        limits = weight_balance_profile["limits"]
        plot_limits["right"] = max(*limits[0], plot_limits["right"])
        plot_limits["bottom"] = min(*limits[1], plot_limits["bottom"])
        plot_limits["left"] = min(*limits[0], plot_limits["left"])
    vertical_range = plot_limits["top"] - plot_limits["bottom"]
    horizontal_range = plot_limits["right"] - plot_limits["left"]
    plot_limits["top"] += 0.25 * vertical_range
    plot_limits["right"] += 0.25 * horizontal_range
    plot_limits["bottom"] -= 0 * vertical_range
    plot_limits["left"] -= 0.25 * horizontal_range

    # Create matplotlib plot
    plt.style.use('seaborn-v0_8-dark')
    for idx, weight_balance_profile in enumerate(weight_balance_profiles):
        data = weight_balance_profile["limits"]
        plt.plot(
            data[0],
            data[1],
            color=colors[idx],
            linestyle=line_styles[idx],
            marker='o',
            linewidth=2,
            markersize=7,
            label=weight_balance_profile["name"]
        )
        plt.fill_between(data[0], data[1],
                         color=colors[idx], alpha=0.12 + 0.06 * idx)

        for i, cg_location in enumerate(data[0]):
            plt.text(
                cg_location,
                data[1][i] + 10,
                f"({cg_location}, {data[1][i]/1000}K)",
                ha="right",
                va="bottom",
                color='#404040',
                fontsize=10
            )

    plt.xlim(plot_limits["left"], plot_limits["right"])
    plt.ylim(plot_limits["bottom"], plot_limits["top"])
    plt.xlabel("C.G. Location [Inches Aft of Datum]")
    plt.ylabel("Aircraft Weight [lbs]")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    # Return the plot as a streaming response
    graph_response = StreamingResponse(
        io.BytesIO(buffer.read()), media_type="image/png")
    graph_response.headers[
        "Content-Disposition"] = 'attachment; filename="weight_and_balance_graph.png"'
    return graph_response


@router.post(
    "/weight-balance-profile/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
def post_new_weight_and_balance_profile(
    profile_id: int,
    data: schemas.WeightBalanceData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
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

    # Check performance profile and permissions.
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )

    # Check maximum number of W&B profiles is 4
    wb_profiles = db_session.query(models.WeightBalanceProfile).filter(
        models.WeightBalanceProfile.performance_profile_id == profile_id
    ).all()

    if len(wb_profiles) >= 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of W&B profiles per performance profile is 4."
        )

    # Check weight and balance profile doesn't already exist
    wb_profile_exists = db_session.query(
        models.WeightBalanceProfile).filter(and_(
            models.WeightBalanceProfile.name == data.name,
            models.WeightBalanceProfile.performance_profile_id == profile_id
        )).first()
    if wb_profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weight and Balance profile {data.name} already exists."
        )

    # Post weight and balance profile
    new_profile = models.WeightBalanceProfile(
        performance_profile_id=profile_id,
        name=data.name
    )
    db_session.add(new_profile)
    db_session.commit()
    db_session.refresh(new_profile)

    # Post weight and balance limits
    wb_profile_id = new_profile.id
    new_limits = [models.WeightBalanceLimit(
        weight_balance_profile_id=wb_profile_id,
        cg_location_in=limit.cg_location_in,
        weight_lb=limit.weight_lb,
        sequence=limit.sequence,
    ) for limit in data.limits]

    db_session.add_all(new_limits)
    db_session.commit()

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )

    # Return weight and balance profile
    weight_balance_profile = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id).first()
    limits = db_session.query(models.WeightBalanceLimit).filter_by(
        weight_balance_profile_id=wb_profile_id).all()

    return {
        **weight_balance_profile.__dict__,
        "limits": [limit.__dict__ for limit in limits]
    }


@router.put(
    "/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PerformanceProfileReturn
)
def edit_weight_and_balance_data_for_performance_profile(
    profile_id: int,
    performance_data: schemas.PerformanceProfileWeightBalanceData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Weight And Balance Data For Performance Profile Endpoint.

    Parameters: 
    - profile_id (int): performance profile id.
    - performance_data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the performance profile data, and the id.

    Raise:
    - HTTPException (400): if performance profile doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check performance profile and permissions.
    performance_profile_query = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=profile_id
    )

    # Update profile
    performance_profile_query.update({
        "center_of_gravity_in": performance_data.center_of_gravity_in,
        "empty_weight_lb": performance_data.empty_weight_lb,
        "max_ramp_weight_lb": performance_data.max_ramp_weight_lb,
        "max_takeoff_weight_lb": performance_data.max_takeoff_weight_lb,
        "max_landing_weight_lb": performance_data.max_landing_weight_lb,
        "baggage_allowance_lb": performance_data.baggage_allowance_lb
    })
    db_session.commit()

    check_completeness_and_make_preferred_if_complete(
        profile_id=profile_id,
        db_session=db_session
    )

    # Return profile
    new_performance_profile = db_session.query(
        models.PerformanceProfile).filter_by(id=profile_id).first()

    fuel_tanks = db_session.query(models.FuelTank).filter_by(
        performance_profile_id=profile_id).all()

    fuel_capacity = sum([tank.fuel_capacity_gallons for tank in fuel_tanks])
    unusable_fuel = sum([tank.unusable_fuel_gallons for tank in fuel_tanks])

    return {
        **new_performance_profile.__dict__,
        "performance_profile_name": new_performance_profile.name,
        "fuel_capacity_gallons": fuel_capacity,
        "unusable_fuel_gallons": unusable_fuel
    }


@router.put(
    "/weight-balance-profile/{wb_profile_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.WeightBalanceReturn
)
def edit_weight_and_balance_profile(
    wb_profile_id: int,
    data: schemas.WeightBalanceData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Weight And Balance Profile Endpoint.

    Parameters: 
    - wb_profile_id (int): weight and balance id.
    - data (dict): the data to be added.

    Returns: 
    - Dic: dictionary with the data added to the database, and the id.

    Raise:
    - HTTPException (400): if weight and balance doesn't exists, or data is wrong.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if W&B ID exists
    wb_profile_query = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id)
    if wb_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"W&B Profile with ID {wb_profile_id} was not found."
        )

    # Check performance profile and permissions.
    performance_profile = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=wb_profile_query.first().performance_profile_id
    ).first()

    # Check weight and balance profile doesn't already exist
    wb_profile_exists = db_session.query(
        models.WeightBalanceProfile).filter(and_(
            models.WeightBalanceProfile.name == data.name,
            models.WeightBalanceProfile.performance_profile_id == performance_profile.id,
            not_(models.WeightBalanceProfile.id == wb_profile_id)
        )).first()
    if wb_profile_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weight and Balance profile '{data.name}' already exists."
        )

    # Update weight and balance limts
    new_limits = [models.WeightBalanceLimit(
        weight_balance_profile_id=wb_profile_id,
        cg_location_in=limit.cg_location_in,
        weight_lb=limit.weight_lb,
        sequence=limit.sequence,
    ) for limit in data.limits]

    _ = db_session.query(models.WeightBalanceLimit).filter(
        models.WeightBalanceLimit.weight_balance_profile_id == wb_profile_id
    ).delete(synchronize_session="evaluate")

    db_session.add_all(new_limits)

    # Update weight and balance profile
    wb_profile_query.update({
        "name": data.name
    })

    db_session.commit()

    # Return weight and balance profile
    weight_balance_profile = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id).first()
    limits = db_session.query(models.WeightBalanceLimit).filter_by(
        weight_balance_profile_id=wb_profile_id).all()

    return {
        **weight_balance_profile.__dict__,
        "limits": [limit.__dict__ for limit in limits]
    }


@router.delete("/weight-balance-profile/{wb_profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight_and_balance_profile(
    wb_profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Weight and Balance Profile Endpoint.

    Parameters: 
    - wb_profile_id (int): weight and balance id.

    Returns: None

    Raise:
    - HTTPException (400): if W&B profile id doesn't exists.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check if W&B ID exists
    wb_profile_query = db_session.query(
        models.WeightBalanceProfile).filter_by(id=wb_profile_id)
    if wb_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"W&B Profile with ID {wb_profile_id} was not found."
        )

    # Check if performance profile and permissions
    performance_profile_id = wb_profile_query.first().performance_profile_id
    _ = check_performance_profile_and_permissions(
        db_session=db_session,
        user_id=get_user_id_from_email(
            email=current_user.email, db_session=db_session
        ),
        user_is_active_admin=current_user.is_active and current_user.is_admin,
        profile_id=performance_profile_id
    ).first()

    # Delete W&B Profile
    deleted = wb_profile_query.delete(synchronize_session=False)
    if not deleted:
        raise common_responses.internal_server_error()

    db_session.commit()

    # Check completeness
    check_completeness_and_make_preferred_if_complete(
        profile_id=performance_profile_id,
        db_session=db_session
    )
