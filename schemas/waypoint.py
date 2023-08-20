"""
Pydantic waypoint scemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data input to the API endpoints.

"""

from typing import Optional, Any

from pydantic import BaseModel, constr, conint, confloat, validator, model_validator


class Waypoint(BaseModel):
    """
    This class defines the pydantic waypoint schema.

   Attributes:
    - code (String): waypoint code identifyer.
    - name (String): waypoint name.
    - is_official (boolean): True if waypoint is an official aviation waypoint.
    - lat_degrees (Integer): latitude degrees of the waypoint coordinates.
    - lat_minutes (Integer): latitude minutes of the waypoint coordinates.
    - lat_seconds (Integer): latitude seconds of the waypoint coordinates.
    - lat_direction (String): latitude direction of the waypoint coordinates ("N" or "S").
    - lon_degrees (Integer): longitude degrees of the waypoint coordinates.
    - lon_minutes (Integer): longitude minutes of the waypoint coordinates.
    - lon_seconds (Integer): longitude seconds of the waypoint coordinates.
    - lon_direction (String): longitude direction of the waypoint coordinates ("E" or "W").
    - magnetic_variation (Integer): magnetic variation at the waypoint.
    """

    code: constr(
        strip_whitespace=True,
        to_upper=True,
        strict=True,
        min_length=2,
        max_length=10,
        pattern='[-a-zA-Z0-9]{2,10}'
    )
    name: constr(strict=True, min_length=2, max_length=50)
    is_official: Optional[bool]
    lat_degrees: conint(strict=True, ge=0, le=90)
    lat_minutes: conint(strict=True, ge=0, le=59)
    lat_seconds: Optional[conint(strict=True, ge=0, le=59)]
    lat_direction: Optional[constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=1,
        pattern='[NSns]'
    )]
    lon_degrees: conint(strict=True, ge=0, le=180)
    lon_minutes: conint(strict=True, ge=0, le=59)
    lon_seconds: Optional[conint(strict=True, ge=0, le=59)]
    lon_direction: Optional[constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=1,
        pattern='[EWew]'
    )]
    magnetic_variation: Optional[confloat(strict=True, allow_inf_nan=False)]

    @validator('magnetic_variation')
    @classmethod
    def round_magnetic_variation(clc, value: float) -> float:
        '''
        Classmethod to round magnetic_variation input value to 1 decimal place.

        Parameters:
        - value (float): The object with the values to be validated.

        Returns:
        (float) : The magnetic_variation value rounded to 1 decimal place.

        '''
        return round(value, 1)

    @model_validator(mode='after')
    @classmethod
    def validate_waypoint_schema(cls, values) -> Any:
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
            "lat": "Latitude must be between S89 59 59 and N90 0 0",
            "lon": "Longitude must be between W179 59 59 and E180 0 0"
        }

        if (
            values.lat_direction == 'N' and
            values.lat_degrees >= 90 and
            (
                values.lat_minutes > 0 or
                values.lat_seconds > 0
            )
        ):
            raise ValueError(err_message['lat'])

        if (
            values.lat_direction == 'S' and
            values.lat_degrees > 89
        ):
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


class Aerodrome(BaseModel):
    """
    This class defines the pydantic aerodrome schema.

   Attributes:
    - has_taf (boolean): true if the airport has a weather TAF.
    - has_metar (boolean): true if the airport has a weather METAR.
    - has_fds (boolean): true if the airport has a weather FDs.
    - elevation (int): airport elevation in ft.
    """

    has_taf: bool
    has_metar: bool
    has_fds: bool
    elevation_ft: int
