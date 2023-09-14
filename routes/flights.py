"""
FastAPI flights router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from datetime import datetime

from fastapi import APIRouter, Depends, status, HTTPException
import pytz
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import get_user_id_from_email
from functions import navigation

router = APIRouter(tags=["Flights"])


def get_basic_flight_data_for_return(flight_id: int, db_session: Session, user_id: int):
    """
    This functions organizes basic flight data for returning to user.
    """
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    departure = db_session.query(models.Departure, models.Aerodrome)\
        .join(models.Aerodrome, models.Departure.aerodrome_id == models.Aerodrome.id)\
        .filter(models.Departure.flight_id == flight_id).first()

    arrival = db_session.query(models.Arrival, models.Aerodrome)\
        .join(models.Aerodrome, models.Arrival.aerodrome_id == models.Aerodrome.id)\
        .filter(models.Arrival.flight_id == flight_id).first()

    legs = db_session.query(models.Leg, models.FlightWaypoint, models.Waypoint)\
        .outerjoin(models.FlightWaypoint, models.Leg.id == models.FlightWaypoint.leg_id)\
        .outerjoin(models.Waypoint, models.FlightWaypoint.waypoint_id == models.Waypoint.id)\
        .filter(models.Leg.flight_id == flight_id).order_by(models.Leg.sequence).all()

    return {
        "id": flight.id,
        "departure_time": pytz.timezone('UTC').localize((flight.departure_time)),
        "aircraft_id": flight.aircraft_id,
        "departure_aerodrome_id": departure[1].id,
        "departure_aerodrome_is_private": departure[1].user_waypoint is not None,
        "arrival_aerodrome_id": arrival[1].id,
        "arrival_aerodrome_is_private": arrival[1].user_waypoint is not None,
        "legs": [{
            "id": leg.id,
            "sequence": leg.sequence,
            "waypoint": {
                "id": wp.id,
                "code": flight_wp.code,
                "lat_degrees": wp.lat_degrees,
                "lat_minutes": wp.lat_minutes,
                "lat_seconds": wp.lat_seconds,
                "lat_direction": wp.lat_direction,
                "lon_degrees": wp.lon_degrees,
                "lon_minutes": wp.lon_minutes,
                "lon_seconds": wp.lon_seconds,
                "lon_direction": wp.lon_direction,
                "magnetic_variation": wp.magnetic_variation
            } if flight_wp is not None else None,
            "altitude_ft": leg.altitude_ft,
            "temperature_c": leg.temperature_c,
            "wind_magnitude_knot": leg.wind_magnitude_knot,
            "wind_direction": leg.wind_direction,
            "weather_valid_from": pytz.timezone('UTC').localize((leg.weather_valid_from))
            if leg.weather_valid_from is not None else None,
            "weather_valid_to": pytz.timezone('UTC').localize((leg.weather_valid_to))
            if leg.weather_valid_to is not None else None,
        } for leg, flight_wp, wp in legs]
    }


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.NewFlightReturn
)
async def post_new_flight(
    flight_data: schemas.NewFlightData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Post New Flight Endpoint.

    Parameters: 
    - flight_data (dict): the flight data to be added.

    Returns: 
    - Dic: dictionary with the flight data and id.

    Raise:
    - HTTPException (400): if flight status already exists, or it
      contains characters other than letters, hyphen and white space.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """
    # Get user ID
    user_id = await get_user_id_from_email(
        email=current_user.email, db_session=db_session)

    # Check aircraft exists and is owned by user
    aircraft = db_session.query(models.Aircraft, models.PerformanceProfile)\
        .join(models.PerformanceProfile,
              models.Aircraft.id == models.PerformanceProfile.aircraft_id)\
        .filter(and_(
            models.Aircraft.id == flight_data.aircraft_id,
            models.Aircraft.owner_id == user_id,
            models.PerformanceProfile.is_preferred.is_(True),
            models.PerformanceProfile.is_complete(True)
        )).first()
    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a valid aircraft ID, or complete the preferred performance profile."
        )

    # Check departure and arrival aerodromes exist
    a = models.Aerodrome
    u = models.UserWaypoint
    v = models.VfrWaypoint
    w = models.Waypoint

    departure = db_session.query(a, u, v, w)\
        .outerjoin(u, a.user_waypoint_id == u.waypoint_id)\
        .outerjoin(v, a.vfr_waypoint_id == v.waypoint_id)\
        .outerjoin(w, u.waypoint_id == w.id)\
        .outerjoin(w, v.waypoint_id == w.id)\
        .filter(and_(
            a.id == flight_data.departure_aerodrome_id,
            or_(
                and_(
                    a.vfr_waypoint_id.isnot(None),
                    not_(v.hidden)
                ),
                u.creator_id == user_id
            )
        )).first()
    if departure is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Departure aerodrome not found."
        )

    arrival = db_session.query(a, u, v, w)\
        .outerjoin(u, a.user_waypoint_id == u.waypoint_id)\
        .outerjoin(v, a.vfr_waypoint_id == v.waypoint_id)\
        .outerjoin(w, u.waypoint_id == w.id)\
        .outerjoin(w, v.waypoint_id == w.id)\
        .filter(and_(
            a.id == flight_data.arrival_aerodrome_id,
            or_(
                a.vfr_waypoint_id.isnot(None),
                u.creator_id == user_id
            )
        )).first()
    if arrival is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arrival aerodrome not found."
        )

    # Check departure time is in the future
    if flight_data.departure_time <= pytz.timezone('UTC').localize(datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UTC estimated departure time, has to be in the future."
        )

    # Post new flight
    new_flight = models.Flight(
        pilot_id=user_id,
        departure_time=flight_data.departure_time,
        aircraft_id=aircraft[0].id,
        status_id=1
    )
    db_session.add(new_flight)
    db_session.commit()
    db_session.refresh(new_flight)
    new_flight_data = {**new_flight.__dict__}

    # Post departure and arrival
    new_departure = models.Departure(
        flight_id=new_flight_data["id"],
        aerodrome_id=departure[0].id
    )
    db_session.add(new_departure)

    new_arrival = models.Arrival(
        flight_id=new_flight_data["id"],
        aerodrome_id=arrival[0].id
    )
    db_session.add(new_arrival)

    # Post Leg
    magnetic_var = navigation.get_magnetic_variation_for_leg(
        from_waypoint=departure[3],
        to_waypoint=arrival[3],
        db_session=db_session
    )
    track_magnetic = departure[3].track_to(arrival[3]) + magnetic_var
    easterly = track_magnetic >= 0 and track_magnetic < 180
    altitude_ft = navigation.round_altitude_to_odd_thousand_plus_500(
        min_altitude=max(
            departure[0].elevation_ft,
            arrival[0].elevation_ft
        ) + 2000
    ) if easterly else\
        navigation.round_altitude_to_even_thousand_plus_500(
            min_altitude=max(
                departure[0].elevation_ft,
                arrival[0].elevation_ft
            ) + 2000
    )
    new_leg = models.Leg(
        sequence=1,
        flight_id=new_flight_data["id"],
        altitude_ft=altitude_ft
    )
    db_session.add(new_leg)

    db_session.commit()
    db_session.refresh(new_leg)

    # Return flight data
    return {
        "id": new_flight_data["id"],
        "departure_time": flight_data.departure_time,
        "aircraft_id": aircraft[0].id,
        "departure_aerodrome_id": departure[0].id,
        "departure_aerodrome_is_private": departure[0].user_waypoint is not None,
        "arrival_aerodrome_id": arrival[0].id,
        "arrival_aerodrome_is_private": arrival[0].user_waypoint is not None,
        "legs": [{
            "id": new_leg.id,
            "sequence": new_leg.sequence,
            "altitude_ft": new_leg.altitude_ft,
            "temperature_c": new_leg.temperature_c,
            "wind_magnitude_knot": new_leg.wind_magnitude_knot
        }]
    }


@router.post(
    "/leg/{flight_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.NewFlightReturn
)
async def post_new_leg(
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
    - List: new list of legs.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not admin user.
    - HTTPException (500): if there is a server error. 
    """

    # Check flight exists
    user_id = await get_user_id_from_email(
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
        new_flight_waypoint = {"code": waypoint_code}

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
        new_flight_waypoint = {"code": leg_data.new_waypoint.code}

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
    magnetic_var = navigation.get_magnetic_variation_for_leg(
        from_waypoint=from_waypoint[1],
        to_waypoint=new_waypoint,
        db_session=db_session
    )
    track_magnetic = from_waypoint[1].track_to(new_waypoint) + magnetic_var
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
    db_session.add(new_waypoint)
    db_session.commit()
    db_session.refresh(new_leg)
    new_flight_waypoint["leg_id"] = new_leg.id
    db_session.refresh(new_waypoint)
    new_flight_waypoint["waypoint_id"] = new_waypoint.id
    db_session.add(models.FlightWaypoint(**new_flight_waypoint))
    db_session.commit()

    # Return flight data
    return get_basic_flight_data_for_return(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )


@router.delete("/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flight(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Flight.

    Parameters: 
    flight_id (int): flight id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    # Create flight query and check if flight exists
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
    flight_query = db_session.query(models.Flight).filter(and_(
        models.Flight.pilot_id == user_id,
        models.Flight.id == flight_id
    ))

    if not flight_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The flight you're trying to delete is not in the database."
        )

    # Get all waypoint IDs
    waypoint_ids = [
        waypoint.waypoint_id for _, waypoint in db_session
        .query(models.Leg, models.FlightWaypoint)
        .outerjoin(models.FlightWaypoint, models.Leg.id == models.FlightWaypoint.leg_id)
        .filter(models.Leg.flight_id == flight_id).all() if waypoint is not None
    ]

    # Delete flight and waypoints
    deleted_flight = flight_query.delete(synchronize_session=False)
    deleterd_waypoints = db_session.query(models.Waypoint)\
        .filter(models.Waypoint.id.in_(waypoint_ids))\
        .delete(synchronize_session=False)
    if not deleted_flight or not deleterd_waypoints:
        raise common_responses.internal_server_error()

    db_session.commit()


@router.delete(
    "/leg/{leg_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.NewFlightReturn
)
async def delete_flight_leg(
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
    - HTTPException (401): invalid credentials.
    - HTTPException (404): status not found.
    - HTTPException (500): if there is a server error. 
    """

    # Check leg exists and user has permission to delete
    user_id = await get_user_id_from_email(email=current_user.email, db_session=db_session)
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
    return get_basic_flight_data_for_return(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )
