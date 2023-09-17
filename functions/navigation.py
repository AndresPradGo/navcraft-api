"""
Useful Functions for Navigation Calculations

Usage: 
- Import the required function and call it.
"""

import math
from typing import List, Dict

from sqlalchemy.orm import Session

import models


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
    other_waypoints.sort(key=lambda w: waypoint.great_arc_to(w))
    return other_waypoints[0]


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


def pressure_altitude(altitude_ft: int, altimeter_inhg: float) -> int:
    """
    This function calculates the pressure altitude in ft, from the actual
     altitude [ft] and an altimeter setting [inHg].
    """
    pressure_alt = round(altitude_ft + 1000 * (29.92 - altimeter_inhg), 0)
    return int(pressure_alt)


def runway_wind_direction(
    wind_magnitude_knot: int,
    wind_direction_true: int,
    runway_number: int,
    magnetic_variation: float
) -> Dict[str, int]:
    """
    This function calculates and returns the runway headwind and cross-wind in knots.
    """

    runway_direction = runway_number * 10 + magnetic_variation
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
