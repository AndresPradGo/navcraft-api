"""
Pydantic waypoint scemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional

from pydantic import BaseModel, constr, conint, confloat, conlist, NaiveDatetime, validator, model_validator

from utils.functions import clean_string


class WaypointBase(BaseModel):
    """
    This class defines the pydantic waypoint_base schema.

   Attributes:
    - code (String): waypoint code identifyer.
    - name (String): waypoint name.
    - lat_degrees (Integer): latitude degrees of the waypoint coordinates.
    - lat_minutes (Integer): latitude minutes of the waypoint coordinates.
    - lat_seconds (Integer): latitude seconds of the waypoint coordinates.
    - lat_direction (String): latitude direction of the waypoint coordinates ("N" or "S").
    - lon_degrees (Integer): longitude degrees of the waypoint coordinates.
    - lon_minutes (Integer): longitude minutes of the waypoint coordinates.
    - lon_seconds (Integer): longitude seconds of the waypoint coordinates.
    - lon_direction (String): longitude direction of the waypoint coordinates ("E" or "W").
    - magnetic_variation (Float): magnetic variation at the waypoint.
    """

    code: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=2,
        max_length=50,
        pattern='^[-a-zA-Z0-9]+$',
    )
    name: constr(min_length=2, max_length=50)
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


class UserWaypointReturn(WaypointBase):
    """
    This class defines the pydantic waypoint_return schema.

    Attributes:
    - id (Integer): waypoint id.
    - name (Optional String): waypoint name.
    - created_at (DateTime): date time created.
    - last_updated (DateTime): date time last updated.
    """

    id: conint(gt=0)
    name: Optional[constr(min_length=2, max_length=50)] = None
    created_at: NaiveDatetime
    last_updated: NaiveDatetime

    class Config():
        from_attributes = True


class VfrWaypointReturn(UserWaypointReturn):
    """
    This class defines the pydantic vfr_waypoint_return schema.

   Attributes:
    - hidden (boolean): if true, do not show waypoint to users.
    """

    hidden: Optional[bool] = None


class UserWaypointData(WaypointBase):
    """
    This class defines the pydantic waypoint_with_validation schema.

    Attributes: None
    """

    @validator('magnetic_variation')
    @classmethod
    def round_magnetic_variation(clc, value: float) -> float:
        '''
        Classmethod to round magnetic_variation input value to 1 decimal place.

        Parameters:
        - value (float): the values to be validated.

        Returns:
        (float) : The magnetic_variation value rounded to 1 decimal place.

        '''
        return round(value, 1)

    @validator('name')
    @classmethod
    def clean_waypoint_name(clc, value: str) -> str:
        '''
        Classmethod to clean name string.

        Parameters:
        - value (str): the name string t to be validated.

        Returns:
        (str): cleaned name string.

        '''
        return clean_string(value)

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


class VfrWaypointData(UserWaypointData):
    """
    This class defines the pydantic vfr_waypoint_data schema.

   Attributes:
    - hidden (boolean): if true, do not show waypoint to users.
    """

    hidden: bool


class FlightWaypointData(WaypointBase):
    """
    This class defines the pydantic flight_waypoint_with_validation schema.

    Attributes: 
     - name (Optional String): waypoint name.
    """
    name: Optional[constr(min_length=2, max_length=50)] = None


class AerodromeBase(BaseModel):
    """
    This class defines the pydantic aerodrome_base schema.

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


class RegisteredAerodromeData(VfrWaypointData, AerodromeBase):
    """
    This class defines the pydantic registered_aerodrome_data schema.
    """
    status: int


class PrivateAerodromeData(UserWaypointData, AerodromeBase):
    """
    This class defines the pydantic private_aerodrome_data schema.
    """
    status: int


class RegisteredAerodromeReturn(VfrWaypointReturn, AerodromeBase):
    """
    This class defines the pydantic registered_aerodrome_return schema.
    """
    status: str
    registered: bool


class PrivateAerodromeReturn(UserWaypointReturn, AerodromeBase):
    """
    This class defines the pydantic private_aerodrome_return schema.
    """
    status: str
    registered: bool


class RunwayInAerodromeReturn(BaseModel):
    """
    This class defines the pydantic schema to return a list 
    of runways inside an aerodrome_return_with_runways model.
    """
    id: conint(gt=0)
    number: conint(
        ge=1,
        le=36
    )
    position: Optional[constr(
        to_upper=True,
        min_length=1,
        max_length=1,
        pattern="^[rRlLcC]$"
    )] = None
    length_ft: int
    surface: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern="^[-a-zA-Z ']+$",
    )
    surface_id: int


class AerodromeReturnWithRunways(RegisteredAerodromeReturn):
    """
    This class defines the pydantic schema to return aerodrome data with a list of runways.
    """
    runways: Optional[conlist(item_type=RunwayInAerodromeReturn)] = []


class AerodromeStatusReturn(BaseModel):
    """
    This class defines the pydantic aerodrome_status_return schema.
    """
    id: int
    status: str
