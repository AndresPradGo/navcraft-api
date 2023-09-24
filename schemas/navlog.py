"""
Pydantic navlog schemas

This module defines the data-structures needed to return navlog calculation results.

Usage: 
- Import the required schema class to validate data at the API endpoints.
"""

from typing import Optional

from pydantic import (
    BaseModel,
    conint,
    confloat,
    constr,
    field_validator,
    model_validator
)


class WaypointInNavLog(BaseModel):
    """
    This class defines the basic waypoint data included in the navigation log:
    """

    code: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=2,
        max_length=50,
        pattern="^['-a-zA-Z0-9]+$",
    )
    name: constr(min_length=2, max_length=255)
    latitude_degrees: confloat(ge=-90, le=90)
    longitude_degrees: confloat(gt=-180, le=180)


class NavigationLogLegResults(BaseModel):
    """
    This class defines the data-structure to return 
    navlog calculation results for one flight leg.
    """

    from_waypoint: WaypointInNavLog
    to_waypoint: WaypointInNavLog
    desired_altitude_ft: conint(ge=0)
    actual_altitud_ft: conint(ge=0)
    truncated_altitude: conint(ge=0)
    rpm: conint(gt=0)
    temperature_c: int
    truncated_temperature_c: int
    ktas: conint(ge=0)
    kcas: conint(ge=0)
    true_track: conint(gt=0, le=360)
    wind_magnitude_knot: conint(ge=0)
    wind_direction: Optional[conint(gt=0, le=360)] = None
    true_heading: conint(gt=0, le=360)
    magnetic_variation: confloat(allow_inf_nan=False)
    magnetic_heading: int
    ground_speed: conint(ge=0)
    distance_to_climb: conint(ge=0)
    distance_enroute: int
    total_distance: conint(ge=0)
    time_to_climb_min: conint(ge=0)
    time_enroute_min: conint(ge=0)
    fuel_to_climb_gallons: confloat(allow_inf_nan=False, ge=0.0)
    cruise_gph: confloat(allow_inf_nan=False, ge=0.0)

    @model_validator(mode='after')
    @classmethod
    def round_float_data(cls, values):
        '''
        Classmethod to round floats to 2 decimal places.
        '''

        values.magnetic_variation = round(values.magnetic_variation, 2)
        values.fuel_to_climb_gallons = round(values.fuel_to_climb_gallons, 2)
        values.cruise_gph = round(values.cruise_gph, 2)

        return values

    @field_validator('magnetic_heading')
    @classmethod
    def round_correct_magnetic_heading(cls, value: int) -> int:
        '''
        Classmethod to bound magnetic heading values within 0 to 360.
        '''
        if value > 360:
            value -= 360
        if value < 0:
            value += 360
        return value