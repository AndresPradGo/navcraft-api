"""
Pydantic flight schemas

This module defines the flight related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional, List

from pydantic import (
    BaseModel,
    conint,
    constr,
    confloat,
    AwareDatetime,
    field_validator,
    model_validator
)


class NewFlightWaypointData(BaseModel):
    """
    This class defines the data-structure required form client to post flight-waypoint data.
    Name is not required and magnetic variation is optional.
    """
    code: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=2,
        max_length=50,
        pattern='^[-a-zA-Z0-9]+$',
    )
    lat_degrees: conint(ge=0, le=90)
    lat_minutes: conint(ge=0, le=59)
    lat_seconds: Optional[conint(ge=0, le=59)] = None
    lat_direction: Optional[constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=1,
        pattern='^[NSns]$'
    )] = None
    lon_degrees: conint(ge=0, le=180)
    lon_minutes: conint(ge=0, le=59)
    lon_seconds: Optional[conint(ge=0, le=59)] = None
    lon_direction: Optional[constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=1,
        pattern='^[EWew]$'
    )] = None
    magnetic_variation: Optional[confloat(allow_inf_nan=False)] = None

    @field_validator('magnetic_variation')
    @classmethod
    def round_magnetic_variation(cls, value: float) -> float | None:
        '''
        Classmethod to round magnetic_variation input value to 1 decimal place.

        Parameters:
        - value (float): the values to be validated.

        Returns:
        (float) : The magnetic_variation value rounded to 1 decimal place.

        '''
        if value is not None:
            return round(value, 1)

        return None

    @model_validator(mode='after')
    @classmethod
    def validate_waypoint_schema(cls, values):
        '''
        Classmethod to check whether the lattitude is between 
        89 59 59 S and 90 0 0 N, and the longitude is between 
        179 59 59 W and 180 0 0 E; as part of the data validation.

        Parameters:
        - values (Any): The object with the values to be validated.

        Returns:
        (Any) : The object of validated values.

        Raises:
        ValueError: Whenever the lattitude or longitud values are not within the desired range.

        '''

        err_message = {
            "lat": "Latitude must be between S89 59 59 and N89 59 59",
            "lon": "Longitude must be between W179 59 59 and E180 0 0"
        }

        if values.lat_degrees > 89:
            raise ValueError(err_message['lat'])

        if (
            values.lon_direction == 'E' and
            values.lon_degrees >= 180 and
            (
                values.lon_minutes > 0 or
                values.lon_seconds > 0
            )
        ):
            raise ValueError(err_message['lon'])

        if (
            values.lon_direction == 'W' and
            values.lon_degrees > 179
        ):
            raise ValueError(err_message['lon'])

        return values


class NewFlightWaypointReturn(NewFlightWaypointData):
    """
    This class defines the data structured returned to 
    the client after posting new flight waypoints.
    """
    id: conint(ge=0)


class NewLegData(BaseModel):
    """
    This class defines the data required to post new flight-legs.
    """
    sequence: conint(ge=1)
    new_waypoint: Optional[NewFlightWaypointData] = None
    existing_waypoint_id: Optional[conint(ge=0)] = None

    @model_validator(mode='after')
    @classmethod
    def validate_waypoint_schema(cls, values):
        '''
        Classmethod to check that only new_waypoint or existing_waypoint_id are provided.

        Parameters:
        - values (Any): The object with the values to be validated.

        Returns:
        (Any) : The object of validated values.

        Raises:
        ValueError: if both new_waypoint and existing_waypoint_id are None.

        '''

        if values.existing_waypoint_id is None and values.new_waypoint is None:
            raise ValueError(
                "Please provide waypoint data, or a valid waypoint id.")
        if values.existing_waypoint_id is not None and values.new_waypoint is not None:
            raise ValueError(
                "Please provide only waypoint data, or a valid waypoint id.")

        return values


class NewLegReturn(BaseModel):
    """
    This class defines the data returned to the client, after posting new flight-legs.
    """
    id: conint(ge=0)
    sequence: conint(ge=1)
    waypoint: Optional[NewFlightWaypointReturn] = None
    altitude_ft: conint(ge=500)
    temperature_c: int
    wind_direction: Optional[conint(gt=0, le=360)] = None
    wind_magnitude_knot: conint(ge=0)
    weather_valid_from: Optional[AwareDatetime] = None
    weather_valid_to: Optional[AwareDatetime] = None


class NewFlightData(BaseModel):
    """
    This class defines the flight data requiered to post a new flight.
    """
    departure_time: AwareDatetime
    aircraft_id: conint(gt=0)
    departure_aerodrome_id: conint(gt=0)
    arrival_aerodrome_id: conint(gt=0)


class NewFlightReturn(NewFlightData):
    """
    This class defines the flight data returned to the client after posting a new flight.
    """
    id: conint(gt=0)
    departure_aerodrome_is_private: bool
    arrival_aerodrome_is_private: bool
    legs: List[NewLegReturn]
