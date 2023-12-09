"""
Useful Functions for Navigation Calculations

Usage: 
- Import the required function and call it.
"""

import math
from typing import List, Dict, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from functions import aircraft_performance
import models
from utils.config import get_constant


def round_altitude_to_nearest_hundred(min_altitude: int) -> int:
    """
    This function rounds a minimum flying altitude to its next hundred, 
    andt returns it.
    """
    remainder = min_altitude % 100
    if remainder == 0:
        return min_altitude
    else:
        return min_altitude + (100 - remainder)


def round_altitude_to_odd_thousand_plus_500(min_altitude: int) -> int:
    """
    This function rounds a minimum flying altitude to its 
    next odd thousand 500 and returns it.
    """
    # Calculate the next odd thousand plus 500
    if round_altitude_to_nearest_hundred(min_altitude) <= 3000:
        return round_altitude_to_nearest_hundred(min_altitude)

    nearest_odd_thousand = (min_altitude // 2000) * 2000 + 1000
    nearest = nearest_odd_thousand + 500

    if nearest < min_altitude:
        return nearest + 2000
    return nearest


def round_altitude_to_even_thousand_plus_500(min_altitude: int) -> int:
    """
    This function rounds a minimum flying altitude to its 
    next even thousand 500 and returns it.
    """
    # Calculate the next even thousand plus 500
    if round_altitude_to_nearest_hundred(min_altitude) <= 3000:
        return round_altitude_to_nearest_hundred(min_altitude)

    nearest = math.ceil(min_altitude / 2000) * 2000 + 500
    return nearest


def find_closest_waypoint(
    waypoint: models.Waypoint,
    other_waypoints: List[models.Waypoint]
) -> models.Waypoint:
    """
    This function finds and resturns the waypoint closest to a given waypoint, 
    from a list of waypoints.
    """
    # pylint: disable=unnecessary-lambda
    other_waypoints.sort(key=lambda w: waypoint.great_arc_to_waypoint(w))
    return other_waypoints[0]


def get_magnetic_variation_for_waypoint(waypoint: models.Waypoint, db_session: Session) -> float:
    """
    This function returns the magnetic variation for a given waypoint.
    """

    if waypoint.magnetic_variation is not None:
        return waypoint.magnetic_variation

    vfr_waypoints = db_session.query(models.Waypoint, models.VfrWaypoint)\
        .join(models.VfrWaypoint, models.Waypoint.id == models.VfrWaypoint.waypoint_id)\
        .filter(models.Waypoint.magnetic_variation.isnot(None))

    waypoints = [row[0] for row in vfr_waypoints]

    closest_waypoint = find_closest_waypoint(
        waypoint=waypoint, other_waypoints=waypoints)

    return closest_waypoint.magnetic_variation


def get_magnetic_variation_for_leg(
        from_waypoint: models.Waypoint,
        to_waypoint: models.Waypoint,
        db_session: Session
) -> float:
    """
    This function returns the magnetic variation for a leg between 2 given waypoints.
    """
    magnetic_var = from_waypoint.get_magnetic_var(to_waypoint)
    if abs(magnetic_var) <= 1e-3:
        vfr_waypoints = db_session.query(models.Waypoint, models.VfrWaypoint)\
            .join(models.VfrWaypoint, models.Waypoint.id == models.VfrWaypoint.waypoint_id)\
            .filter(models.Waypoint.magnetic_variation.isnot(None))

        waypoints = [row[0] for row in vfr_waypoints]

        closest_to_origin = find_closest_waypoint(
            waypoint=from_waypoint,
            other_waypoints=waypoints
        )
        closest_to_destination = find_closest_waypoint(
            waypoint=from_waypoint,
            other_waypoints=waypoints
        )

        magnetic_var = (closest_to_origin.get_magnetic_var(
            closest_to_destination))

    return magnetic_var


def pressure_altitude_converter(
    altimeter_inhg: float,
    altitude_ft: int,
    reverse: bool = False
) -> int:
    """
    This function calculates the pressure altitude in ft, from the true
     altitude [ft] and an altimeter setting [inHg]. If revere is set to True, 
     the function calculated the true altitude from pressure altitude.
    """
    if reverse:
        return int(round(altitude_ft - 1000 * (29.92 - altimeter_inhg), 0))
    return int(round(altitude_ft + 1000 * (29.92 - altimeter_inhg), 0))


def runway_wind_direction(
    wind_magnitude_knot: int,
    wind_direction_true: int,
    runway_number: int,
    magnetic_variation: float
) -> Dict[str, int]:
    """
    This function calculates and returns the runway headwind and cross-wind in knots.
    """

    runway_direction = runway_number * 10 - magnetic_variation
    wind_angle = math.radians(wind_direction_true - runway_direction)

    return {
        "headwind": int(round(wind_magnitude_knot * math.cos(wind_angle), 0)),
        "crosswind": int(round(wind_magnitude_knot * math.sin(wind_angle), 0))
    }


def wind_calculations(
    ktas: int,
    true_track: int,
    wind_magnitude_knot: int,
    wind_direction_true: int
) -> Dict[str, int]:
    """
    This function calculates and returns the groundspeed in knots and the true headding.
    """
    # Angles in radians
    wind_angle = math.radians(wind_direction_true)
    track_angle = math.radians(true_track)

    # Calculate groundspeed and wind correction angle
    ground_speed = ktas - wind_magnitude_knot * \
        math.cos(wind_angle - track_angle)
    wind_correction_angle_rad = math.atan(
        wind_magnitude_knot * math.sin(wind_angle - track_angle) / ktas
    )

    # Calculate and correct true heading
    true_heading = true_track + math.degrees(wind_correction_angle_rad)
    true_heading = true_heading - 360 if true_heading > 360 else 360 + \
        true_heading if true_heading < 0 else true_heading

    # Retrurn Results
    return {
        "ground_speed": int(round(ground_speed, 0)),
        "true_heading": int(round(true_heading, 0))
    }


def calculate_cas_from_tas(
    ktas: int,
    pressure_alt_ft: int,
    temperature_c: int,
) -> int:
    """
    This function calculates KCAS from KTAS.
    """

    # Define constants
    air_constant = get_constant("air_constant_j_kg_k")
    standard_density = get_constant("standard_density_kg_m3")
    temperature_k = temperature_c + 273.15
    pressure_pa = (1013.25 - pressure_alt_ft / 30) * 100

    # Calculate and return CAS
    kcas = int(ktas / math.sqrt(air_constant * temperature_k *
                                standard_density / pressure_pa))

    return kcas


def get_takeoff_weight(flight_id: int, db_session: Session):
    """
    This function calculates and returns the takeoff weight for a given flight.
    """

    # Get Persons on board
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
    ).filter(
        models.PersonOnBoard.flight_id == flight_id
    ).all()

    pobs_weight = float(sum((
        pob.weight_lb if pob.weight_lb is not None
        else user_weight if user_weight is not None
        else passenger_weight
        for pob, user_weight, passenger_weight in persons
    )))

    # Get baggages
    baggages = db_session.query(models.Baggage).filter(
        models.Baggage.flight_id == flight_id
    ).all()

    baggages_weight = float(sum((baggage.weight_lb for baggage in baggages)))

    # Get total fuel gallons
    fuel_tanks = db_session.query(models.Fuel).filter(
        models.Fuel.flight_id == flight_id
    ).all()

    fuel_gallons = float(sum((fuel_tank.gallons for fuel_tank in fuel_tanks)))

    # Get aircraft data
    flight = db_session.query(models.Flight).filter_by(id=flight_id).first()
    aircraft_id = flight.aircraft_id
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

    density = float(db_session.query(models.FuelType).filter_by(
        id=performance_profile[0].fuel_type_id
    ).first().density_lb_gal)

    pre_takeoff_fuel_burn_weight = float(
        -performance_profile[0].take_off_taxi_fuel_gallons) * density
    empty_weight = float(performance_profile[0].empty_weight_lb)

    # Calculate and return weight
    takeoff_weight = round(sum((
        empty_weight,
        pobs_weight,
        baggages_weight,
        fuel_gallons * density,
        pre_takeoff_fuel_burn_weight
    )), 2)

    return takeoff_weight


def calculate_leg_nav_log(
    profile_id: int,
    leg: models.Leg,
    from_to_names_codes: Tuple[Dict[str, str]],
    origin_waypoint: models.Waypoint,
    destination_waypoint: models.Waypoint,
    initial_pressure_alt: int,
    weight_lb: int,
    bhp_percent: int,
    db_session: Session
):
    """
    This function returns all the navigation log values for one flight leg.
    """

    # Get basic leg values
    total_distance = origin_waypoint.great_arc_to_waypoint(
        destination_waypoint)
    true_track = origin_waypoint.true_track_to_waypoint(destination_waypoint)
    magnetic_var = get_magnetic_variation_for_leg(
        from_waypoint=origin_waypoint,
        to_waypoint=destination_waypoint,
        db_session=db_session
    )
    pressure_alt_ft = pressure_altitude_converter(
        altimeter_inhg=float(leg.altimeter_inhg),
        altitude_ft=leg.altitude_ft
    )
    # Get climb values
    climb_results, pressure_alt_achived = aircraft_performance.get_climb_data(
        profile_id=profile_id,
        weight_lb=weight_lb,
        pressure_alt_from_ft=initial_pressure_alt,
        pressure_alt_to_ft=pressure_alt_ft,
        temperature_c=leg.temperature_c,
        available_distance_nm=total_distance,
        db_session=db_session
    )

    actual_altitude_ft = pressure_altitude_converter(
        altimeter_inhg=float(leg.altimeter_inhg),
        altitude_ft=pressure_alt_achived,
        reverse=True
    )

    distance_to_climb = min(climb_results["distance_nm"], total_distance)

    # Get cruise values
    cruise_results, cruise_truncated_values = aircraft_performance.get_cruise_data(
        profile_id=profile_id,
        weight_lb=weight_lb,
        pressure_alt_ft=pressure_alt_ft,
        temperature_c=leg.temperature_c,
        bhp_percent=bhp_percent,
        db_session=db_session
    )

    truncated_altitude = pressure_altitude_converter(
        altimeter_inhg=float(leg.altimeter_inhg),
        altitude_ft=cruise_truncated_values["pressure_alt_ft"],
        reverse=True
    )
    truncated_temperature = cruise_truncated_values["temperature_c"]

    # Get heading, groundspeed and calibrated airspeed
    wind_direction = leg.wind_direction if leg.wind_direction is not None else 0
    wind_calculation_results = wind_calculations(
        ktas=cruise_results["ktas"],
        true_track=true_track,
        wind_magnitude_knot=leg.wind_magnitude_knot,
        wind_direction_true=wind_direction
    )
    kcas = calculate_cas_from_tas(
        ktas=cruise_results["ktas"],
        pressure_alt_ft=pressure_alt_ft,
        temperature_c=leg.temperature_c,
    )
    magnetic_heading = int(
        round(wind_calculation_results["true_heading"] + magnetic_var, 0))
    time_enroute_min = round(max(
        total_distance - climb_results["distance_nm"],
        0
    ) * 60 / wind_calculation_results["ground_speed"], 0)

    # Return nav-log data
    return {
        "from_waypoint": {
            "code": from_to_names_codes[0]["code"],
            "name": from_to_names_codes[0]["name"],
            "latitude_degrees": math.degrees(origin_waypoint.lat()),
            "longitude_degrees": math.degrees(origin_waypoint.lon()),
        },
        "to_waypoint": {
            "code": from_to_names_codes[1]["code"],
            "name": from_to_names_codes[1]["name"],
            "latitude_degrees": math.degrees(destination_waypoint.lat()),
            "longitude_degrees": math.degrees(destination_waypoint.lon()),
        },
        "desired_altitude_ft": leg.altitude_ft,
        "actual_altitud_ft": actual_altitude_ft,
        "truncated_altitude": truncated_altitude,
        "rpm": cruise_results["rpm"],
        "temperature_c": leg.temperature_c,
        "truncated_temperature_c": truncated_temperature,
        "ktas": cruise_results["ktas"],
        "kcas": kcas,
        "true_track": true_track,
        "wind_magnitude_knot": leg.wind_magnitude_knot,
        "wind_direction": leg.wind_direction,
        "true_heading": wind_calculation_results["true_heading"],
        "magnetic_variation": magnetic_var,
        "magnetic_heading": magnetic_heading,
        "ground_speed": wind_calculation_results["ground_speed"],
        "distance_to_climb": distance_to_climb,
        "distance_enroute": int(round(total_distance - climb_results["distance_nm"], 0)),
        "total_distance": int(round(total_distance, 0)),
        "time_to_climb_min": climb_results["time_min"],
        "time_enroute_min": time_enroute_min,
        "fuel_to_climb_gallons": climb_results["fuel_gal"],
        "cruise_gph": cruise_results["gph"],
    }


def calculate_nav_log(
    profile_id: int,
    legs: List[models.Leg],
    waypoints: List[models.Waypoint],
    waypoint_names_codes: List[Dict[str, str]],
    pressure_altitude_at_departure_aerodrome: float,
    takeoff_weight: int,
    bhp_percent: int,
    fuel_density: float,
    fuel_gallons: float,
    db_session: Session
):
    """
    This function calculates all the navigation log values for the whole flight,
    and returns it as a list of values per leg.
    """
    nav_log_data = []
    total_fuel_to_climb = 0
    hours_enroute = 0
    total_gallons_enroute = 0

    weight = takeoff_weight
    initial_pressure_alt = pressure_altitude_at_departure_aerodrome
    for idx, leg in enumerate(legs):
        leg_nav_log_data = calculate_leg_nav_log(
            profile_id=profile_id,
            leg=leg,
            from_to_names_codes=(
                waypoint_names_codes[idx],
                waypoint_names_codes[idx + 1]
            ),
            origin_waypoint=waypoints[idx],
            destination_waypoint=waypoints[idx + 1],
            initial_pressure_alt=initial_pressure_alt,
            weight_lb=weight,
            bhp_percent=bhp_percent,
            db_session=db_session
        )
        leg_nav_log_data["leg_id"] = leg.id
        nav_log_data.append(leg_nav_log_data)

        initial_pressure_alt = pressure_altitude_converter(
            altitude_ft=leg.altitude_ft,
            altimeter_inhg=float(leg.altimeter_inhg)
        )
        gallons_to_climb = leg_nav_log_data["fuel_to_climb_gallons"]
        total_fuel_to_climb += gallons_to_climb
        gallons_enroute = leg_nav_log_data["cruise_gph"] * \
            leg_nav_log_data["time_enroute_min"] / 60
        hours_enroute += leg_nav_log_data["time_enroute_min"] / 60
        total_gallons_enroute += gallons_enroute
        gallons_burned = gallons_to_climb + gallons_enroute
        if fuel_gallons >= gallons_burned:
            fuel_gallons -= gallons_burned
        else:
            fuel_gallons = 0
            gallons_burned = fuel_gallons
        weight_fuel_burned = gallons_burned * fuel_density
        weight -= weight_fuel_burned

    fuel_data = {
        "climb_gallons": float(round(total_fuel_to_climb, 2)),
        "hours_enroute": float(round(hours_enroute, 2)),
        "gallons_enroute": float(round(total_gallons_enroute, 2))
    }

    return nav_log_data, fuel_data


def location_coordinate(lat_deg: float, lon_deg: float, strict: bool = False) -> Dict[str, Union[int, str]]:
    """
    This function receives the latitude and longitude of a location, 
    and returns a dictionary with the latitude and longitude in degree, 
    minutes, secodns and direction ("N", "S", "E", "W").
    """

    location = {
        "lat_degrees": 0,
        "lat_minutes": 0,
        "lat_seconds": 0,
        "lat_direction": "N",
        "lon_degrees": 0,
        "lon_minutes": 0,
        "lon_seconds": 0,
        "lon_direction": "W",
    }

    location["lat_direction"] = "N" if lat_deg >= 0 else "S"
    location["lat_degrees"] = int(math.floor(abs(lat_deg)))
    lat_min_residual = (abs(lat_deg) - location["lat_degrees"]) * 60
    location["lat_minutes"] = int(math.floor(lat_min_residual))
    location["lat_seconds"] = min(int(round(
        (lat_min_residual - location["lat_minutes"]) * 60)), 59) if strict else int(round(
            (lat_min_residual - location["lat_minutes"]) * 60))

    location["lon_direction"] = "E" if lon_deg >= 0 else "W"
    location["lon_degrees"] = int(math.floor(abs(lon_deg)))
    lon_min_residual = (abs(lon_deg) - location["lon_degrees"]) * 60
    location["lon_minutes"] = int(math.floor(lon_min_residual))
    location["lon_seconds"] = min(int(round(
        (lon_min_residual - location["lon_minutes"]) * 60)), 59) if strict else int(round(
            (lon_min_residual - location["lon_minutes"]) * 60))

    return location
