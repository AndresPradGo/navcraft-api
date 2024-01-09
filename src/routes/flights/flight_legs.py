"""
FastAPI flight Legs router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import (
    get_user_id_from_email,
    get_extensive_flight_data_for_return
)
from functions import navigation

router = APIRouter(tags=["Flight Legs"])


@router.post(
    "/{flight_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.ExtensiveFlightDataReturn
)
def post_new_leg(
    flight_id: int,
    leg_data: schemas.NewLegData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Leg Endpoint.

    Parameters: 
    - flight_id (int): flight id.
    - flight_data (dict): the flight data to be added.

    Returns: 
    - Dict: flight data.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exists
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight ID is not valid."
        )

    # Get all legs
    legs_query = db_session.query(models.Leg)\
        .filter(models.Leg.flight_id == flight_id)\
        .order_by(models.Leg.sequence)

    # Check sequence is not out of range
    if leg_data.sequence > legs_query.all()[-1].sequence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Make sure the leg sequence is within range."
        )

    # Check waypoint data and create waypoint object
    if leg_data.existing_waypoint_id is not None:
        w_model = models.Waypoint
        u_model = models.UserWaypoint
        v_model = models.VfrWaypoint

        waypoint = db_session.query(w_model, u_model, v_model)\
            .outerjoin(u_model, u_model.waypoint_id == w_model.id)\
            .outerjoin(v_model, v_model.waypoint_id == w_model.id)\
            .filter(and_(
                w_model.id == leg_data.existing_waypoint_id,
                or_(
                    not_(v_model.hidden),
                    u_model.creator_id == user_id
                )
            )).first()

        if waypoint is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Waypoint not found."
            )

        is_user_waypoint = waypoint[1] is not None
        waypoint_code = waypoint[1].code if is_user_waypoint\
            else waypoint[2].code
        waypoint_name = waypoint[1].name if is_user_waypoint\
            else waypoint[2].name

        new_waypoint = models.Waypoint(
            lat_degrees=waypoint[0].lat_degrees,
            lat_minutes=waypoint[0].lat_minutes,
            lat_seconds=waypoint[0].lat_seconds,
            lat_direction=waypoint[0].lat_direction,
            lon_degrees=waypoint[0].lon_degrees,
            lon_minutes=waypoint[0].lon_minutes,
            lon_seconds=waypoint[0].lon_seconds,
            lon_direction=waypoint[0].lon_direction,
            magnetic_variation=waypoint[0].magnetic_variation
        )
        new_flight_waypoint = {
            "code": waypoint_code,
            "name": waypoint_name,
            "from_user_waypoint": is_user_waypoint,
            "from_vfr_waypoint": not is_user_waypoint
        }

    else:
        new_waypoint = models.Waypoint(
            lat_degrees=leg_data.new_waypoint.lat_degrees,
            lat_minutes=leg_data.new_waypoint.lat_minutes,
            lat_seconds=leg_data.new_waypoint.lat_seconds,
            lat_direction=leg_data.new_waypoint.lat_direction,
            lon_degrees=leg_data.new_waypoint.lon_degrees,
            lon_minutes=leg_data.new_waypoint.lon_minutes,
            lon_seconds=leg_data.new_waypoint.lon_seconds,
            lon_direction=leg_data.new_waypoint.lon_direction,
            magnetic_variation=leg_data.new_waypoint.magnetic_variation
        )
        new_flight_waypoint = {
            "code": leg_data.new_waypoint.code,
            "name": leg_data.new_waypoint.name
        }

    # Update sequence of legs that go after the new leg
    legs_to_update = [
        {
            "id": leg.id,
            "sequence": leg.sequence + 1,
            "altitude_ft": leg.altitude_ft
        } for leg in legs_query.all() if leg.sequence >= leg_data.sequence
    ]
    for leg in legs_to_update:
        db_session.query(models.Leg).filter_by(id=leg["id"]).update(leg)

    # Add new leg
    from_waypoint = db_session.query(models.FlightWaypoint, models.Waypoint)\
        .join(models.Waypoint, models.FlightWaypoint.waypoint_id == models.Waypoint.id)\
        .filter(models.FlightWaypoint.leg_id == legs_to_update[0]["id"]).first()
    if from_waypoint is None:
        departure_aerodrome_id = db_session.query(models.Departure).filter(
            models.Departure.flight_id == flight_id
        ).first().aerodrome_id

        if departure_aerodrome_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to add new leg. Please add a departure aerodrome to this flight before making any other changes."
            )
        from_waypoint = db_session.query(models.Waypoint).filter_by(
            id=departure_aerodrome_id
        ).first()
    else:
        from_waypoint = from_waypoint[1]

    magnetic_var = navigation.get_magnetic_variation_for_leg(
        from_waypoint=from_waypoint,
        to_waypoint=new_waypoint,
        db_session=db_session
    )
    track_magnetic = from_waypoint.true_track_to_waypoint(
        new_waypoint) + magnetic_var
    easterly = track_magnetic >= 0 and track_magnetic < 180
    altitude_ft = navigation.round_altitude_to_odd_thousand_plus_500(
        min_altitude=legs_to_update[0]["altitude_ft"]
    ) if easterly else\
        navigation.round_altitude_to_even_thousand_plus_500(
            min_altitude=legs_to_update[0]["altitude_ft"]
    )
    new_leg = models.Leg(
        altitude_ft=altitude_ft,
        sequence=leg_data.sequence,
        flight_id=flight_id
    )
    db_session.add(new_leg)

    # Add waypoint
    new_waypoint.in_north_airspace = new_waypoint.is_in_northern_airspace()
    db_session.add(new_waypoint)
    db_session.commit()
    db_session.refresh(new_leg)
    new_flight_waypoint["leg_id"] = new_leg.id
    db_session.refresh(new_waypoint)
    new_flight_waypoint["waypoint_id"] = new_waypoint.id
    db_session.add(models.FlightWaypoint(**new_flight_waypoint))
    db_session.commit()

    # Return flight data
    return get_extensive_flight_data_for_return(
        flight_ids=[flight_id],
        db_session=db_session,
        user_id=user_id
    )[0]


@router.put(
    "/{leg_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.ExtensiveFlightDataReturn
)
def edit_flight_leg(
    leg_id: int,
    leg_data: schemas.UpdateLegData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit Flight Leg Endpoint.

    Parameters: 
    - leg_id (int): flight leg id.
    - leg_data (dict[UpdateLegData]): the flight leg data to be added.

    Returns: 
    - dict[ExtensiveFlightDataReturn]: flight data.

    Raise:
    - HTTPException (400): if flight leg doesn't exist, or data is wrong.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Check flight exists
    leg_query = db_session.query(models.Leg).filter_by(id=leg_id)

    if leg_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leg ID is not valid."
        )
    flight_id = leg_query.first().flight_id

    # Check user has permission to update flight
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not Authorized to update this flight."
        )

    # Check waypoint data and update waypoint
    updating_final_leg = leg_query.first().sequence == len(
        db_session.query(models.Leg).filter_by(flight_id=flight_id).all())

    if not updating_final_leg:
        if leg_data.existing_waypoint_id is not None:
            w_model = models.Waypoint
            u_model = models.UserWaypoint
            v_model = models.VfrWaypoint

            waypoint = db_session.query(w_model, u_model, v_model)\
                .outerjoin(u_model, u_model.waypoint_id == w_model.id)\
                .outerjoin(v_model, v_model.waypoint_id == w_model.id)\
                .filter(and_(
                    w_model.id == leg_data.existing_waypoint_id,
                    or_(
                        not_(v_model.hidden),
                        u_model.creator_id == user_id
                    )
                )).first()

            if waypoint is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Waypoint not found."
                )

            is_user_waypoint = waypoint[1] is not None
            waypoint_code = waypoint[1].code if is_user_waypoint\
                else waypoint[2].code
            waypoint_name = waypoint[1].name if is_user_waypoint\
                else waypoint[2].name

            flight_waypoint_query = db_session.query(models.FlightWaypoint).filter(
                models.FlightWaypoint.leg_id == leg_query.first().id
            )
            db_session.query(models.Waypoint).filter(
                models.Waypoint.id == flight_waypoint_query.first().waypoint_id
            ).update({
                "lat_degrees": waypoint[0].lat_degrees,
                "lat_minutes": waypoint[0].lat_minutes,
                "lat_seconds": waypoint[0].lat_seconds,
                "lat_direction": waypoint[0].lat_direction,
                "lon_degrees": waypoint[0].lon_degrees,
                "lon_minutes": waypoint[0].lon_minutes,
                "lon_seconds": waypoint[0].lon_seconds,
                "lon_direction": waypoint[0].lon_direction,
                "magnetic_variation": waypoint[0].magnetic_variation,
                "in_north_airspace": waypoint[0].in_north_airspace
            })
            flight_waypoint_query.update({
                "code": waypoint_code,
                "name": waypoint_name,
                "from_user_waypoint": is_user_waypoint,
                "from_vfr_waypoint": not is_user_waypoint
            })

        elif leg_data.new_waypoint is not None:
            flight_waypoint_query = db_session.query(models.FlightWaypoint).filter(
                models.FlightWaypoint.leg_id == leg_query.first().id
            )
            new_waypoint = models.Waypoint(
                lat_degrees=leg_data.new_waypoint.lat_degrees,
                lat_minutes=leg_data.new_waypoint.lat_minutes,
                lat_seconds=leg_data.new_waypoint.lat_seconds,
                lat_direction=leg_data.new_waypoint.lat_direction,
                lon_degrees=leg_data.new_waypoint.lon_degrees,
                lon_minutes=leg_data.new_waypoint.lon_minutes,
                lon_seconds=leg_data.new_waypoint.lon_seconds,
                lon_direction=leg_data.new_waypoint.lon_direction,
                magnetic_variation=leg_data.new_waypoint.magnetic_variation
            )
            new_waypoint.in_north_airspace = new_waypoint.is_in_northern_airspace()
            db_session.query(models.Waypoint).filter(
                models.Waypoint.id == flight_waypoint_query.first().waypoint_id
            ).update({
                "lat_degrees": new_waypoint.lat_degrees,
                "lat_minutes": new_waypoint.lat_minutes,
                "lat_seconds": new_waypoint.lat_seconds,
                "lat_direction": new_waypoint.lat_direction,
                "lon_degrees": new_waypoint.lon_degrees,
                "lon_minutes": new_waypoint.lon_minutes,
                "lon_seconds": new_waypoint.lon_seconds,
                "lon_direction": new_waypoint.lon_direction,
                "magnetic_variation": new_waypoint.magnetic_variation,
                "in_north_airspace": new_waypoint.in_north_airspace,
            })
            flight_waypoint_query.update({
                "code": leg_data.new_waypoint.code,
                "name": leg_data.new_waypoint.name,
                "from_user_waypoint": False,
                "from_vfr_waypoint": False
            })

    # Update Leg
    leg_query.update({
        "altitude_ft": leg_data.altitude_ft,
        "temperature_c": leg_data.temperature_c,
        "altimeter_inhg": leg_data.altimeter_inhg,
        "wind_direction": leg_data.wind_direction,
        "wind_magnitude_knot": leg_data.wind_magnitude_knot,
        "temperature_last_updated": leg_data.temperature_last_updated,
        "wind_last_updated": leg_data.wind_last_updated,
        "altimeter_last_updated": leg_data.altimeter_last_updated
    })

    db_session.commit()

    # Return flight data
    return get_extensive_flight_data_for_return(
        flight_ids=[flight_id],
        db_session=db_session,
        user_id=user_id
    )[0]


@router.put(
    "/update-waypoints/{flight_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.UpdateWaypointsReturn
)
def update_flight_waypoints(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Update Flight Waypoints Endpoint.

    Parameters: 
    - flight_id (int): flight id.

    Returns: 
    - dict[UpdateWaypointsReturn]: detailed flight data, and 
      list of waypoints not found.

    Raise:
    - HTTPException (400): if flight doesn't exist, or data is wrong.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Check flight exists and user has permission to update flight
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not Authorized to update this flight."
        )

    leg_ids = [leg.id for leg in db_session.query(
        models.Leg).filter_by(flight_id=flight_id).all()]

    # Get all flight-waypoints
    flight_waypoints = db_session.query(models.FlightWaypoint).filter(
        models.FlightWaypoint.leg_id.in_(leg_ids)
    ).all()
    flight_waypoints_from_user = [
        waypoint for waypoint in flight_waypoints if waypoint.from_user_waypoint
    ]
    flight_waypoints_from_vfr = [
        waypoint for waypoint in flight_waypoints if waypoint.from_vfr_waypoint
    ]

    # Updata user-waypoints
    user_waypoints_not_found = []
    for flight_waypoint_from_user in flight_waypoints_from_user:
        user_waypoint = db_session.query(
            models.UserWaypoint,
            models.Waypoint
        ).join(
            models.Waypoint,
            models.UserWaypoint.waypoint_id == models.Waypoint.id
        ).filter(and_(
            models.UserWaypoint.code == flight_waypoint_from_user.code,
            models.UserWaypoint.creator_id == user_id
        )).first()

        if user_waypoint is None:
            user_waypoints_not_found.append({
                "waypoint_id": flight_waypoint_from_user.waypoint_id,
                "code": flight_waypoint_from_user.code
            })
        else:
            db_session.query(models.FlightWaypoint).filter_by(
                waypoint_id=flight_waypoint_from_user.waypoint_id
            ).update({
                "name": user_waypoint[0].name
            })

            db_session.query(models.Waypoint).filter_by(
                id=flight_waypoint_from_user.waypoint_id
            ).update({
                "lat_degrees": user_waypoint[1].lat_degrees,
                "lat_minutes": user_waypoint[1].lat_minutes,
                "lat_seconds": user_waypoint[1].lat_seconds,
                "lat_direction": user_waypoint[1].lat_direction,
                "lon_degrees": user_waypoint[1].lon_degrees,
                "lon_minutes": user_waypoint[1].lon_minutes,
                "lon_seconds": user_waypoint[1].lon_seconds,
                "lon_direction": user_waypoint[1].lon_direction,
                "magnetic_variation": user_waypoint[1].magnetic_variation,
                "in_north_airspace": user_waypoint[1].in_north_airspace
            })

    # Updata vfr-waypoints
    vfr_waypoints_not_found = []
    for flight_waypoint_from_vfr in flight_waypoints_from_vfr:
        vfr_waypoint = db_session.query(
            models.VfrWaypoint,
            models.Waypoint
        ).join(
            models.Waypoint,
            models.VfrWaypoint.waypoint_id == models.Waypoint.id
        ).filter(and_(
            models.VfrWaypoint.code == flight_waypoint_from_vfr.code,
            models.VfrWaypoint.hidden.is_(False)
        )).first()

        if vfr_waypoint is None:
            vfr_waypoints_not_found.append({
                "waypoint_id": flight_waypoint_from_vfr.waypoint_id,
                "code": flight_waypoint_from_vfr.code
            })
        else:
            db_session.query(models.FlightWaypoint).filter_by(
                waypoint_id=flight_waypoint_from_vfr.waypoint_id
            ).update({
                "name": vfr_waypoint[0].name
            })

            db_session.query(models.Waypoint).filter_by(
                id=flight_waypoint_from_vfr.waypoint_id
            ).update({
                "lat_degrees": vfr_waypoint[1].lat_degrees,
                "lat_minutes": vfr_waypoint[1].lat_minutes,
                "lat_seconds": vfr_waypoint[1].lat_seconds,
                "lat_direction": vfr_waypoint[1].lat_direction,
                "lon_degrees": vfr_waypoint[1].lon_degrees,
                "lon_minutes": vfr_waypoint[1].lon_minutes,
                "lon_seconds": vfr_waypoint[1].lon_seconds,
                "lon_direction": vfr_waypoint[1].lon_direction,
                "magnetic_variation": vfr_waypoint[1].magnetic_variation,
                "in_north_airspace": vfr_waypoint[1].in_north_airspace
            })

    db_session.commit()

    # Return
    return {
        "flight_data": get_extensive_flight_data_for_return(
            flight_ids=[flight_id],
            db_session=db_session,
            user_id=user_id
        )[0],
        "user_waypoints_not_found": user_waypoints_not_found,
        "vfr_waypoints_not_found": vfr_waypoints_not_found
    }


@router.delete(
    "/{leg_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ExtensiveFlightDataReturn
)
def delete_flight_leg(
    leg_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Flight Leg.

    Parameters: 
    leg_id (int): leg id.

    Returns: None

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    # Check leg exists and user has permission to delete
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    leg_query_results = db_session.query(models.Leg, models.Flight)\
        .join(models.Flight, models.Leg.flight_id == models.Flight.id)\
        .filter(and_(models.Leg.id == leg_id, models.Flight.pilot_id == user_id)).first()

    if leg_query_results is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leg not found."
        )

    flight_id = leg_query_results[1].id

    # Check Leg is not the last leg
    leg_ids = [
        leg[0] for leg in db_session.query(models.Leg.id).filter(
            models.Leg.flight_id == flight_id
        ).order_by(models.Leg.sequence).all()
    ]
    leg_is_last = leg_id == leg_ids[-1]
    if leg_is_last:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The last leg of the flight cannot be deleted."
        )

    # Find waypoin ID
    waypoint_id = db_session.query(models.FlightWaypoint.waypoint_id).filter(
        models.FlightWaypoint.leg_id == leg_id).first()[0]

    # Delete leg and waypoint
    leg_deleted = db_session.query(models.Leg).filter(
        models.Leg.id == leg_id).delete(synchronize_session=False)

    waypoint_deleted = db_session.query(models.Waypoint).filter_by(
        id=waypoint_id).delete(synchronize_session=False)

    if not leg_deleted or not waypoint_deleted:
        raise common_responses.internal_server_error()

    db_session.commit()

    # Update sequence
    new_leg_sequence_list = [
        {"id": leg.id, "sequence": seq + 1} for seq, leg in enumerate(
            db_session.query(models.Leg).filter_by(flight_id=flight_id)
            .order_by(models.Leg.sequence).all()
        )
    ]

    for new_leg_sequence in new_leg_sequence_list:
        db_session.query(models.Leg).filter_by(
            id=new_leg_sequence["id"]).update(new_leg_sequence)

    db_session.commit()

    # Return new flight data
    return get_extensive_flight_data_for_return(
        flight_ids=[flight_id],
        db_session=db_session,
        user_id=user_id
    )[0]
