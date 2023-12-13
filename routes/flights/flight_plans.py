"""
FastAPI navigation log router

This module defines the FastAPI flights endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""
from typing import List, Dict
import io

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
from sqlalchemy import and_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import csv_tools as csv
from utils.config import get_table_header
from utils.db import get_db
from functions import navigation
from functions.aircraft_performance import get_landing_takeoff_data
from functions.data_processing import get_user_id_from_email

router = APIRouter(tags=["Flight Plan"])


def get_nav_log_and_fuel_calculations(
    flight_id: int,
    db_session: Session,
    user_id: int
):
    """
    This reusable function prepares all the nav-log and fuel data,
    and returns the results.
    """

    # Get flight and check permissions
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    # Get performance_profile
    aircraft = db_session.query(
        models.PerformanceProfile,
        models.Aircraft
    ).join(
        models.Aircraft,
        models.PerformanceProfile.aircraft_id == models.Aircraft.id
    ).filter(and_(
        models.Aircraft.id == flight.aircraft_id,
        models.PerformanceProfile.is_preferred.is_(True),
        models.PerformanceProfile.is_complete.is_(True)
    )).first()

    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aircraft does not have a preferred performance profile."
        )

    performance_profile = aircraft[0]

    # Get departure and arrival waypoints
    departure_arrival_models = [
        models.Departure,
        models.Arrival
    ]
    departure_arrival_waypoints = []
    aerodromes_weather = []
    for departure_arrival_model in departure_arrival_models:
        departure_arrival = db_session.query(departure_arrival_model, models.Aerodrome).join(
            models.Aerodrome,
            departure_arrival_model.aerodrome_id == models.Aerodrome.id
        ).filter(and_(
            departure_arrival_model.flight_id == flight_id,
            departure_arrival_model.aerodrome_id.isnot(None)
        )).first()
        if departure_arrival is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please make sure the flight has a departure and arrival aerodrome."
            )
        aerodromes_weather.append(departure_arrival)
        if departure_arrival[1].vfr_waypoint_id is not None:
            departure_arrival_waypoint = db_session.query(
                models.VfrWaypoint,
                models.Waypoint
            ).join(
                models.Waypoint,
                models.VfrWaypoint.waypoint_id == models.Waypoint.id
            ).filter(models.VfrWaypoint.waypoint_id == departure_arrival[1].vfr_waypoint_id).first()
        else:
            departure_arrival_waypoint = db_session.query(
                models.UserWaypoint,
                models.Waypoint
            ).join(
                models.Waypoint,
                models.UserWaypoint.waypoint_id == models.Waypoint.id
            ).filter(
                models.UserWaypoint.waypoint_id == departure_arrival[1].user_waypoint_id
            ).first()

        departure_arrival_waypoints.append(departure_arrival_waypoint)

    # Get legs and flight waypoints
    legs_query_results = db_session.query(
        models.Leg,
        models.FlightWaypoint,
        models.Waypoint
    ).outerjoin(
        models.FlightWaypoint,
        models.Leg.id == models.FlightWaypoint.leg_id
    ).outerjoin(
        models.Waypoint,
        models.FlightWaypoint.waypoint_id == models.Waypoint.id
    ).filter(
        models.Leg.flight_id == flight_id
    ).order_by(models.Leg.sequence).all()

    legs = [leg for leg, _, _ in legs_query_results]

    # Organize waypoint data
    waypoints = [waypoint for _, _,
                 waypoint in legs_query_results if waypoint is not None]
    waypoints.insert(0, departure_arrival_waypoints[0][1])
    waypoints.append(departure_arrival_waypoints[1][1])

    waypoint_names_codes = [{
        "name": waypoint.name,
        "code": waypoint.code
    } for _, waypoint, _ in legs_query_results if waypoint is not None]
    waypoint_names_codes.insert(0, {
        "name": departure_arrival_waypoints[0][0].name,
        "code": departure_arrival_waypoints[0][0].code
    })
    waypoint_names_codes.append({
        "name": departure_arrival_waypoints[1][0].name,
        "code": departure_arrival_waypoints[1][0].code
    })

    pressure_alt_at_departure = navigation.pressure_altitude_converter(
        altitude_ft=aerodromes_weather[0][1].elevation_ft,
        altimeter_inhg=float(aerodromes_weather[0][0].altimeter_inhg)
    )

    # Get fuel density
    fuel_type = db_session.query(models.FuelType).filter_by(
        id=performance_profile.fuel_type_id).first()
    fuel_density = float(fuel_type.density_lb_gal)

    # Get total fuel gallons
    fuel_tanks = db_session.query(models.Fuel).filter(
        models.Fuel.flight_id == flight_id
    ).all()

    fuel_gallons = float(sum((fuel_tank.gallons for fuel_tank in fuel_tanks)))

    # Get and return nav log and fuel data
    nav_log_data, fuel_data = navigation.calculate_nav_log(
        profile_id=performance_profile.id,
        legs=legs,
        waypoints=waypoints,
        waypoint_names_codes=waypoint_names_codes,
        pressure_altitude_at_departure_aerodrome=pressure_alt_at_departure,
        takeoff_weight=navigation.get_takeoff_weight(
            flight_id=flight_id,
            db_session=db_session
        ),
        bhp_percent=flight.bhp_percent,
        fuel_density=fuel_density,
        fuel_gallons=fuel_gallons,
        db_session=db_session
    )

    fuel_data["pre_takeoff_gallons"] = float(
        performance_profile.take_off_taxi_fuel_gallons)
    fuel_data["added_enroute_time_hours"] = float(
        flight.added_enroute_time_hours)
    fuel_data["reserve_fuel_hours"] = float(flight.reserve_fuel_hours)
    fuel_data["contingency_fuel_hours"] = float(flight.contingency_fuel_hours)
    fuel_data["gallons_on_board"] = round(fuel_gallons, 2)

    return nav_log_data, fuel_data


def get_weight_balance_calculations(
    flight_id: int,
    db_session: Session,
    user_id: int
):
    """
    This reusable function prepares all the weight and balance report data,
    and returns the results.
    """
    # Check flight exists and get flight data
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )

    aircraft_id = flight.aircraft_id
    warnings = []

    # Get performance profile id
    if aircraft_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight doesn't have an aircraft."
        )
    performance_profile = db_session.query(
        models.PerformanceProfile,
        models.Aircraft
    ).join(
        models.Aircraft,
        models.PerformanceProfile.aircraft_id == models.Aircraft.id
    ).filter(and_(
        models.Aircraft.id == aircraft_id,
        models.PerformanceProfile.is_preferred.is_(True),
        models.PerformanceProfile.is_complete.is_(True)
    )).first()

    if performance_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The flight's aircraft doesn't have preferred performance profile."
        )

    # Prepare seat row list
    seat_rows = db_session.query(models.SeatRow).filter(
        models.SeatRow.performance_profile_id == performance_profile[0].id
    ).order_by(models.SeatRow.arm_in).all()

    seats = []
    for seat_row in seat_rows:
        persons = db_session.query(
            models.PersonOnBoard,
            models.User.weight_lb,
            models.PassengerProfile.weight_lb
        ).outerjoin(
            models.User,
            models.PersonOnBoard.user_id == models.User.id
        ).outerjoin(
            models.PassengerProfile,
            models.PersonOnBoard.passenger_profile_id == models.PassengerProfile.id
        ).filter(and_(
            models.PersonOnBoard.seat_row_id == seat_row.id,
            models.PersonOnBoard.flight_id == flight_id
        )).all()

        total_weight = round(float(sum((
            pob.weight_lb if pob.weight_lb is not None
            else user_weight if user_weight is not None
            else passenger_weight
            for pob, user_weight, passenger_weight in persons
        ))), 2)

        seats.append({
            "weight_lb": total_weight,
            "arm_in": seat_row.arm_in,
            "moment_lb_in": float(seat_row.arm_in) * total_weight,
            "seat_row_id": seat_row.id,
            "seat_row_name": seat_row.name
        })

        if seat_row.weight_limit_lb is not None and seat_row.weight_limit_lb < total_weight:
            warnings.append(
                f"{seat_row.name} can only hold {seat_row.weight_limit_lb} lbs!!!"
            )

    # Prepare baggage compartment list
    baggage_compartments = db_session.query(models.BaggageCompartment).filter(
        models.BaggageCompartment.performance_profile_id == performance_profile[0].id
    ).order_by(models.BaggageCompartment.arm_in).all()

    compartments = []
    for baggage_compartment in baggage_compartments:
        baggages = db_session.query(models.Baggage).filter(and_(
            models.Baggage.baggage_compartment_id == baggage_compartment.id,
            models.Baggage.flight_id == flight_id
        )).all()

        total_weight = round(
            float(sum((baggage.weight_lb for baggage in baggages))), 2)

        compartments.append({
            "weight_lb": total_weight,
            "arm_in": baggage_compartment.arm_in,
            "moment_lb_in": float(baggage_compartment.arm_in) * total_weight,
            "baggage_compartment_id": baggage_compartment.id,
            "baggage_compartment_name": baggage_compartment.name
        })

        if baggage_compartment.weight_limit_lb is not None and\
                baggage_compartment.weight_limit_lb < total_weight:
            warnings.append(
                f"{baggage_compartment.name} can only hold {baggage_compartment.weight_limit_lb} lbs!!!"
            )

    if performance_profile[0].baggage_allowance_lb is not None:
        total_baggage_lbs = sum((baggage["weight_lb"]
                                for baggage in compartments))
        if performance_profile[0].baggage_allowance_lb < total_baggage_lbs:
            warnings.append(
                f"This aircraft can only hold {performance_profile[0].baggage_allowance_lb} lbs of baggage!!!"
            )

    # Prepare fuel on board
    fuel_density = float(db_session.query(models.FuelType).filter_by(
        id=performance_profile[0].fuel_type_id
    ).first().density_lb_gal)
    fuel_tanks = db_session.query(models.FuelTank).filter(
        models.FuelTank.performance_profile_id == performance_profile[0].id
    ).order_by(models.FuelTank.burn_sequence).all()

    fuel_on_board = []
    for fuel_tank in fuel_tanks:
        fuel = db_session.query(models.Fuel).filter(and_(
            models.Fuel.fuel_tank_id == fuel_tank.id,
            models.Fuel.flight_id == flight_id
        )).first()

        total_weight = round(fuel_density * float(fuel.gallons), 2)

        fuel_on_board.append({
            "weight_lb": total_weight,
            "arm_in": float(fuel_tank.arm_in),
            "moment_lb_in": float(fuel_tank.arm_in) * total_weight,
            "gallons": float(fuel.gallons),
            "fuel_tank_id": fuel_tank.id,
            "fuel_tank_name": fuel_tank.name,
            "sequence": fuel_tank.burn_sequence
        })

    # Prepare fuel burned before takeoff
    _, fuel_data = get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    pre_takeoff_fuel_gallons = float(fuel_data["pre_takeoff_gallons"])
    pre_takeoff_fuel_weight = - \
        round(pre_takeoff_fuel_gallons * fuel_density, 2)
    pre_takeoff_fuel_arm = float(fuel_on_board[0]["arm_in"])
    fuel_burned_pre_takeoff = {
        "gallons": pre_takeoff_fuel_gallons,
        "weight_lb": pre_takeoff_fuel_weight,
        "arm_in": pre_takeoff_fuel_arm,
        "moment_lb_in": round(pre_takeoff_fuel_weight * pre_takeoff_fuel_arm, 2),
    }

    # Get total gallons burned
    average_gph = round(
        fuel_data["gallons_enroute"] / fuel_data["hours_enroute"], 1)
    gallons_burned = float(sum((
        fuel_data["added_enroute_time_hours"] * average_gph,
        fuel_data["climb_gallons"],
        fuel_data["gallons_enroute"]
    )))

    fuel_burn_sequences = {tank.burn_sequence for tank in fuel_tanks}

    # Organice fuel burned by burn sequence
    tanks_grouped_by_sequence = []
    for seq in fuel_burn_sequences:
        tanks = [
            {
                **fuel_tank
            } for fuel_tank in fuel_on_board if fuel_tank["sequence"] == seq
        ]
        tanks.sort(key=lambda tank: tank["gallons"])
        tanks_grouped_by_sequence.append(
            {"sequence": seq, "fuel_tanks": tanks})

    # Remove fuel burned before takeoff (assumes there is enough fuel in tanks for takeoff)

    num_tanks_with_sequence = len(tanks_grouped_by_sequence[0]["fuel_tanks"])
    fuel_burned_per_tank = pre_takeoff_fuel_gallons / num_tanks_with_sequence
    for idx in range(len(tanks_grouped_by_sequence[0]["fuel_tanks"])):
        tank_gallons = tanks_grouped_by_sequence[0]["fuel_tanks"][idx]["gallons"] - \
            fuel_burned_per_tank
        tank_weight = round(tank_gallons * fuel_density, 2)
        tank_moment = tank_weight * \
            float(tanks_grouped_by_sequence[0]["fuel_tanks"][idx]["arm_in"])
        tanks_grouped_by_sequence[0]["fuel_tanks"][idx]["gallons"] = tank_gallons
        tanks_grouped_by_sequence[0]["fuel_tanks"][idx]["weight_lb"] = tank_weight
        tanks_grouped_by_sequence[0]["fuel_tanks"][idx]["moment_lb_in"] = tank_moment

    # Calculate fuel-burn per tank
    fuel_burned = []
    idx = 0
    while gallons_burned >= 5e-3 and idx < len(tanks_grouped_by_sequence):
        tanks_with_sequence = tanks_grouped_by_sequence[idx]
        total_gallons_in_tanks = sum((
            tank["gallons"] for tank in tanks_with_sequence["fuel_tanks"]
        ))
        enough_fuel_in_tanks = gallons_burned <= total_gallons_in_tanks
        if not enough_fuel_in_tanks:
            for tank_with_seq in tanks_with_sequence['fuel_tanks']:

                fuel_burned.append({
                    "weight_lb": tank_with_seq["weight_lb"] * (1 if tank_with_seq["weight_lb"] < 0 else -1),
                    "arm_in": tank_with_seq["arm_in"],
                    "moment_lb_in": tank_with_seq["moment_lb_in"] * (1 if tank_with_seq["moment_lb_in"] < 0 else -1),
                    "gallons": tank_with_seq["gallons"],
                    "fuel_tank_id": tank_with_seq["fuel_tank_id"],
                    "fuel_tank_name": tank_with_seq["fuel_tank_name"]
                })
                gallons_burned -= total_gallons_in_tanks
        else:
            sub_idx = 0
            gallons_left_in_tanks_with_seq = [
                {**tank} for tank in tanks_with_sequence["fuel_tanks"]]
            while gallons_burned >= 5e-3 and sub_idx < len(tanks_with_sequence):
                emptiest_tank = gallons_left_in_tanks_with_seq[sub_idx]
                tanks_left = len(tanks_with_sequence["fuel_tanks"]) - sub_idx
                gallons_to_burn_per_tank = gallons_burned / tanks_left
                enough_fuel_in_all_tanks = emptiest_tank["gallons"] >= gallons_to_burn_per_tank
                if not enough_fuel_in_all_tanks:
                    gallons_to_burn_per_tank = emptiest_tank["gallons"]
                sub_sub_idx = sub_idx
                while sub_sub_idx < len(gallons_left_in_tanks_with_seq):
                    gallons_left_in_tanks_with_seq[sub_sub_idx]["gallons"] -=\
                        gallons_to_burn_per_tank
                    sub_sub_idx += 1
                sub_idx += 1
                gallons_burned -= gallons_to_burn_per_tank * tanks_left

            for sub_idx, tank_with_seq in enumerate(tanks_with_sequence["fuel_tanks"]):
                gallons_burned_in_tank = tank_with_seq["gallons"] -\
                    gallons_left_in_tanks_with_seq[sub_idx]["gallons"]
                weight_burned_in_tank = round(
                    gallons_burned_in_tank * fuel_density, 2)
                moment_of_fuel_burned = weight_burned_in_tank * \
                    (tank_with_seq["arm_in"])
                fuel_burned.append(
                    {
                        "weight_lb": weight_burned_in_tank * (1 if weight_burned_in_tank < 0 else -1),
                        "arm_in": tank_with_seq["arm_in"],
                        "moment_lb_in": moment_of_fuel_burned * (1 if moment_of_fuel_burned < 0 else -1),
                        "gallons": gallons_burned_in_tank,
                        "fuel_tank_id": tank_with_seq["fuel_tank_id"],
                        "fuel_tank_name": tank_with_seq["fuel_tank_name"]
                    }
                )

        idx += 1

    # Prepare empty weight
    empty_weight = {
        "weight_lb":  float(performance_profile[0].empty_weight_lb),
        "arm_in": float(performance_profile[0].center_of_gravity_in),
        "moment_lb_in": float(performance_profile[0].empty_weight_lb) *
        float(performance_profile[0].center_of_gravity_in),
    }

    # Prepare zero-fuel weight data
    zero_fuel_weight_lbs = sum((
        float(performance_profile[0].empty_weight_lb),
        sum((seat["weight_lb"] for seat in seats)),
        sum((compartment["weight_lb"] for compartment in compartments))
    ))
    zero_fuel_weight_moment = sum((
        float(performance_profile[0].empty_weight_lb) *
        float(performance_profile[0].center_of_gravity_in),
        sum((seat["moment_lb_in"] for seat in seats)),
        sum((compartment["moment_lb_in"] for compartment in compartments))
    ))
    zero_fuel_weight = {
        "weight_lb": zero_fuel_weight_lbs,
        "arm_in": zero_fuel_weight_moment / zero_fuel_weight_lbs,
        "moment_lb_in": zero_fuel_weight_moment,
    }

    # Prepare ramp weight data
    ramp_weight_lbs = zero_fuel_weight_lbs + \
        sum((fuel["weight_lb"] for fuel in fuel_on_board))
    ramp_weight_moment = zero_fuel_weight_moment + \
        sum((fuel["moment_lb_in"] for fuel in fuel_on_board))
    ramp_weight = {
        "weight_lb": ramp_weight_lbs,
        "arm_in": ramp_weight_moment / ramp_weight_lbs,
        "moment_lb_in": ramp_weight_moment,
    }

    if performance_profile[0].max_ramp_weight_lb is not None and\
            performance_profile[0].max_ramp_weight_lb < ramp_weight_lbs:
        warnings.append(
            f"Maximum ramp weight of {performance_profile[0].max_ramp_weight_lb} lbs exceeded!!!"
        )

    # Prepare takeoff weight data
    takeoff_weight_lbs = ramp_weight_lbs + fuel_burned_pre_takeoff["weight_lb"]
    takeoff_weight_moment = ramp_weight_moment + \
        fuel_burned_pre_takeoff["moment_lb_in"]
    takeoff_weight = {
        "weight_lb": takeoff_weight_lbs,
        "arm_in": takeoff_weight_moment / takeoff_weight_lbs,
        "moment_lb_in": takeoff_weight_moment,
    }

    if performance_profile[0].max_takeoff_weight_lb is not None and\
            performance_profile[0].max_takeoff_weight_lb < takeoff_weight_lbs:
        warnings.append(
            f"Maximum takeoff weight of {performance_profile[0].max_takeoff_weight_lb} lbs exceeded!!!"
        )

    # Prepare Landing weight data
    landing_weight_lbs = takeoff_weight_lbs + \
        sum((fuel["weight_lb"] for fuel in fuel_burned))
    landing_weight_moment = takeoff_weight_moment + \
        sum((fuel["moment_lb_in"] for fuel in fuel_burned))
    landing_weight = {
        "weight_lb": landing_weight_lbs,
        "arm_in": landing_weight_moment / landing_weight_lbs,
        "moment_lb_in": landing_weight_moment,
    }

    if performance_profile[0].max_landing_weight_lb is not None and\
            performance_profile[0].max_landing_weight_lb < landing_weight_lbs:
        warnings.append(
            f"Maximum landing weight of {performance_profile[0].max_landing_weight_lb} lbs exceeded!!!"
        )

    # Prepare W&B-limits warnings
    weight_balance_profile_limits = db_session.query(
        models.WeightBalanceProfile,
        models.WeightBalanceLimit
    ).join(
        models.WeightBalanceLimit,
        models.WeightBalanceProfile.id == models.WeightBalanceLimit.weight_balance_profile_id
    ).filter(
        models.WeightBalanceProfile.performance_profile_id == performance_profile[0].id
    ).order_by(
        models.WeightBalanceProfile.id,
        models.WeightBalanceLimit.sequence
    ).all()

    wb_profile_names = {p.name for p, _ in weight_balance_profile_limits}

    def is_point_under_graph(
        graph_points: List[models.WeightBalanceLimit],
        test_point: Dict[str, float]
    ):
        for i in range(len(graph_points) - 1):
            x1, y1 = float(graph_points[i].cg_location_in), float(
                graph_points[i].weight_lb)
            x2, y2 = float(
                graph_points[i + 1].cg_location_in), float(graph_points[i + 1].weight_lb)
            if (x1 <= float(test_point["arm_in"]) <= x2 or
                    x2 <= float(test_point["arm_in"]) <= x1) and \
                    float(test_point["weight_lb"]) < ((y2 - y1) / (x2 - x1))\
                * (float(test_point["arm_in"]) - x1) + y1:
                return True
        return False

    for wb_profile in wb_profile_names:
        limits = [
            l for p, l in weight_balance_profile_limits if p.name == wb_profile]

        if (not is_point_under_graph(limits, landing_weight)):
            warnings.append(f"Landing Weight exceeds the {wb_profile} limits.")
        if (not is_point_under_graph(limits, takeoff_weight)):
            warnings.append(f"Takeoff Weight exceeds the {wb_profile} limits.")

    # Organize return data
    return {
        "warnings": warnings,
        "seats": seats,
        "compartments": compartments,
        "fuel_on_board": fuel_on_board,
        "fuel_burned_pre_takeoff": fuel_burned_pre_takeoff,
        "fuel_burned": fuel_burned,
        "empty_weight": empty_weight,
        "zero_fuel_weight": zero_fuel_weight,
        "ramp_weight": ramp_weight,
        "takeoff_weight": takeoff_weight,
        "landing_weight": landing_weight,
        "performance_profile_id": performance_profile[0].id,
        "max_takeoff_weight_lb": performance_profile[0].max_takeoff_weight_lb
    }


@router.get(
    "/nav-log/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.NavigationLogLegResults]
)
def navigation_log(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Navigation Log Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - list: list of dictionaries with the nav-log data per leg.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    nav_log_data, _ = get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    return nav_log_data


@router.get(
    "/nav-log/csv/{flight_id}",
    status_code=status.HTTP_200_OK
)
def download_navigation_log_csv_file(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Navigation Log CSV File Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - CSV file: csv file with with the nav-log data per leg.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    nav_log_data, _ = get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    table_name = f'navLog_{nav_log_data[0]["from_waypoint"]["code"]}_{nav_log_data[-1]["to_waypoint"]["code"]}'
    headers = get_table_header("nav_log")

    table_data = [{
        headers["from_waypoint"]: leg["from_waypoint"]["code"],
        headers["to_waypoint"]: leg["to_waypoint"]["code"],
        headers["actual_altitud_ft"]: leg["actual_altitud_ft"],
        headers["rpm"]: leg["rpm"],
        headers["temperature_c"]: leg["temperature_c"],
        headers["ktas"]: leg["ktas"],
        headers["kcas"]: leg["kcas"],
        headers["true_track"]: leg["true_track"],
        headers["wind"]: f"{'0' if leg['wind_direction'] < 100 else ''}{leg['wind_direction']}/{leg['wind_magnitude_knot']}" if leg['wind_direction'] is not None and leg['wind_magnitude_knot'] > 0 else "-",
        headers["true_heading"]: leg["true_heading"],
        headers["magnetic_variation"]: leg["magnetic_variation"],
        headers["magnetic_heading"]: leg["magnetic_heading"],
        headers["ground_speed"]: leg["ground_speed"],
        headers["distance_to_climb"]: leg["distance_to_climb"],
        headers["distance_enroute"]: leg["distance_enroute"],
        headers["total_distance"]: leg["total_distance"],
        headers["time_to_climb_min"]: leg["time_to_climb_min"],
        headers["time_enroute_min"]: leg["time_enroute_min"],
        headers["total_time"]: leg["time_to_climb_min"] + leg["time_enroute_min"],
    } for leg in nav_log_data] if len(nav_log_data) > 0 else [{
        headers["from_waypoint"]: "",
        headers["to_waypoint"]: "",
        headers["actual_altitud_ft"]: "",
        headers["rpm"]: "",
        headers["temperature_c"]: "",
        headers["ktas"]: "",
        headers["kcas"]: "",
        headers["true_track"]: "",
        headers["wind"]: "",
        headers["true_heading"]: "",
        headers["magnetic_variation"]: "",
        headers["magnetic_heading"]: "",
        headers["ground_speed"]: "",
        headers["distance_to_climb"]: "",
        headers["distance_enroute"]: "",
        headers["total_distance"]: "",
        headers["time_to_climb_min"]: "",
        headers["time_enroute_min"]: "",
        headers["total_time"]: "",
    }]

    buffer = csv.list_to_buffer(data=table_data)

    # Prepare and return response
    csv_response = StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
    )
    csv_response.headers["Content-Disposition"] = f'attachment; filename="{table_name}.csv"'
    csv_response.headers["filename"] = f'{table_name}.csv'

    return csv_response


@router.get(
    "/fuel-calculations/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.FuelCalculationResults
)
def fuel_calculations(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Fuel Calculations Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - dict: dictionary with the fuel calculation results.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Get fuel data
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    _, fuel_data = get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    average_gph = round(
        fuel_data["gallons_enroute"] / fuel_data["hours_enroute"], 1)

    # Return data
    return {
        "pre_takeoff_gallons": fuel_data["pre_takeoff_gallons"],
        "climb_gallons": fuel_data["climb_gallons"],
        "average_gph": average_gph,
        "enroute_fuel": {
            "hours": fuel_data["hours_enroute"],
            "gallons": round(fuel_data["hours_enroute"] * average_gph, 2)
        },
        "additional_fuel": {
            "hours": fuel_data["added_enroute_time_hours"],
            "gallons": round(fuel_data["added_enroute_time_hours"] * average_gph, 2)
        },
        "reserve_fuel": {
            "hours": fuel_data["reserve_fuel_hours"],
            "gallons": round(fuel_data["reserve_fuel_hours"] * average_gph, 2)
        },
        "contingency_fuel": {
            "hours": fuel_data["contingency_fuel_hours"],
            "gallons": round(fuel_data["contingency_fuel_hours"] * average_gph, 2)
        },
        "gallons_on_board": fuel_data["gallons_on_board"],
    }


@router.get(
    "/takeoff-landing-distances/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.TakeoffAndLandingDistances
)
def takeoff_and_landing_distances(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Takeoff And Landing Distances Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - dict: dictionary with the takeoff and landing distance data.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Get flight and check permissions
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    flight = db_session.query(models.Flight).filter(and_(
        models.Flight.id == flight_id,
        models.Flight.pilot_id == user_id
    )).first()

    if flight is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight not found."
        )
    # Get performance_profile
    aircraft = db_session.query(
        models.PerformanceProfile,
        models.Aircraft
    ).join(
        models.Aircraft,
        models.PerformanceProfile.aircraft_id == models.Aircraft.id
    ).filter(and_(
        models.Aircraft.id == flight.aircraft_id,
        models.PerformanceProfile.is_preferred.is_(True),
        models.PerformanceProfile.is_complete.is_(True)
    )).first()

    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aircraft does not have a preferred performance profile."
        )

    performance_profile = aircraft[0]

    # Get takeoff and landing weight
    takeoff_weight = navigation.get_takeoff_weight(
        flight_id=flight_id,
        db_session=db_session
    )

    _, fuel_data = get_nav_log_and_fuel_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    average_gph = round(
        fuel_data["gallons_enroute"] / fuel_data["hours_enroute"], 1)

    gallons_burned = float(sum((
        fuel_data["pre_takeoff_gallons"],
        fuel_data["climb_gallons"],
        fuel_data["gallons_enroute"],
        fuel_data["added_enroute_time_hours"] * average_gph
    )))

    fuel_type = db_session.query(models.FuelType).filter_by(
        id=performance_profile.fuel_type_id).first()
    fuel_density = float(fuel_type.density_lb_gal)

    landing_weight = takeoff_weight - gallons_burned * fuel_density

    # Loop for departure and arrival
    loop_parameters = {
        "departure": {
            "model": models.Departure,
            "weight": takeoff_weight
        },
        "arrival": {
            "model": models.Arrival,
            "weight": landing_weight
        }
    }
    takeoff_landing_result = {}
    for key, parameters in loop_parameters.items():
        # Get aerodrome and weather
        departure_arrival = db_session.query(parameters["model"], models.Aerodrome).join(
            models.Aerodrome,
            parameters["model"].aerodrome_id == models.Aerodrome.id
        ).filter(and_(
            parameters["model"].flight_id == flight_id,
            parameters["model"].aerodrome_id.isnot(None)
        )).first()
        if departure_arrival is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please make sure the flight has a departure and arrival aerodrome."
            )

        # Get runways
        runways = db_session.query(models.Runway).filter(
            models.Runway.aerodrome_id == departure_arrival[1].id
        ).all()

        # Loop through runways
        results_per_runway = []
        for runway in runways:
            pressure_alt = navigation.pressure_altitude_converter(
                altitude_ft=departure_arrival[1].elevation_ft,
                altimeter_inhg=float(departure_arrival[0].altimeter_inhg)
            )
            waypoint_id = departure_arrival[1].vfr_waypoint_id\
                if departure_arrival[1].vfr_waypoint_id is not None\
                else departure_arrival[1].user_waypoint_id

            waypoint = db_session.query(
                models.Waypoint).filter_by(id=waypoint_id).first()
            magnetic_variation = navigation.get_magnetic_variation_for_leg(
                from_waypoint=waypoint,
                to_waypoint=waypoint,
                db_session=db_session
            )

            wind_components = navigation.runway_wind_direction(
                wind_magnitude_knot=departure_arrival[0].wind_magnitude_knot,
                wind_direction_true=departure_arrival[0].wind_direction,
                runway_number=runway.number,
                magnetic_variation=magnetic_variation
            )

            # Get groundroll and obstacle clearance distances
            performance_data, performance_data_truncated_inputs = get_landing_takeoff_data(
                profile_id=performance_profile.id,
                is_takeoff=key == "departure",
                weight_lb=parameters["weight"],
                pressure_alt_ft=pressure_alt,
                temperature_c=departure_arrival[0].temperature_c,
                runway_surface_id=runway.surface_id,
                head_wind=wind_components["headwind"],
                db_session=db_session
            )

            # Organize runway data
            prefix = '0' if runway.number < 10 else ''
            suffix = runway.position if runway.position is not None else ''
            runway_length = runway.length_ft if key == "departure" else runway.landing_length_ft
            results_per_runway.append({
                "runway_id": runway.id,
                "runway": f"{prefix}{runway.number}{suffix}",
                "length_available_ft": runway_length,
                "intersection_departure_length": runway.intersection_departure_length_ft,
                "weight_lb": takeoff_weight if key == "departure" else landing_weight,
                "pressure_altitude_ft": pressure_alt,
                "truncated_pressure_altitude_ft": performance_data_truncated_inputs["pressure_alt_ft"],
                "temperature_c": departure_arrival[0].temperature_c,
                "truncated_temperature_c": performance_data_truncated_inputs["temperature_c"],
                "headwind_knot": wind_components["headwind"],
                "x_wind_knot": wind_components["crosswind"],
                "ground_roll_ft": performance_data["groundroll_ft"],
                "obstacle_clearance_ft": performance_data["obstacle_clearance_ft"],
            })

        takeoff_landing_result[key] = results_per_runway

    return takeoff_landing_result


@router.get(
    "/weight-balance/{flight_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.WeightAndBalanceReport
)
def weight_and_balance_report(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Weight and Balance Report Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - Dict: W&B Report data.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    return get_weight_balance_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )


@router.get(
    "/weight-balance-graph/{flight_id}",
    status_code=status.HTTP_200_OK
)
async def weight_and_balance_graph(
    flight_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Weight and Balance Graph Endpoint.

    Parameters:
    - flight_id (int): flight id.

    Returns: 
    - Png-file: W&B graph.

    Raise:
    - HTTPException (400): if flight doesn't exist.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Define line graph style variables
    colors = ['#00D5C8', '#D500CB', '#4AD500', '#D50000']
    line_styles = ['-', '--', '-.', ':']

    labels = ('ZFW', 'Landing', 'Takeoff')
    label_positions = (('right', 'bottom'),
                       ('left', 'top'), ('right', 'bottom'))
    labels_offset = ((-0.2, 1), (0.2, 1), (-0.2, 1))

    # Get weight and balance data
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    weight_balance_data = get_weight_balance_calculations(
        flight_id=flight_id,
        db_session=db_session,
        user_id=user_id
    )

    zf_weight = weight_balance_data["zero_fuel_weight"]
    landing_weight = weight_balance_data["landing_weight"]
    takeoff_weight = weight_balance_data["takeoff_weight"]

    arm_data = (zf_weight["arm_in"],
                landing_weight["arm_in"], takeoff_weight["arm_in"])
    weight_data = (
        zf_weight["weight_lb"], landing_weight["weight_lb"], takeoff_weight["weight_lb"])

    # Get weight and balance profiles
    weight_balance_profile_limits = db_session.query(
        models.WeightBalanceProfile,
        models.WeightBalanceLimit
    ).join(
        models.WeightBalanceLimit,
        models.WeightBalanceProfile.id == models.WeightBalanceLimit.weight_balance_profile_id
    ).filter(
        models.WeightBalanceProfile.performance_profile_id == weight_balance_data[
            "performance_profile_id"]
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
        "top": float(weight_balance_data["max_takeoff_weight_lb"]),
        "right": 0,
        "bottom": float(weight_balance_data["max_takeoff_weight_lb"]),
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

    plt.plot(
        arm_data,
        weight_data,
        color='#ff6206',
        linestyle='-',
        marker='X',
        linewidth=3,
        markeredgecolor='k',
        markersize=9
    )
    for i, label in enumerate(labels):
        plt.text(
            arm_data[i] + labels_offset[i][0],
            weight_data[i] + labels_offset[i][1],
            label,
            ha=label_positions[i][0],
            va=label_positions[i][1],
            fontweight='bold',
            fontsize=15
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
