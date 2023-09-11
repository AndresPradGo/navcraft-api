"""
Pydantic waypoint schemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional

from pydantic import (
    BaseModel,
    constr,
    conint,
    confloat,
    conlist,
    AwareDatetime,
    field_validator,
    model_validator
)

from utils.functions import clean_string


class WaypointBase(BaseModel):
    """
    This class defines the basic waypoint data:
    - code
    - name
    - coordinates
    - magnetic variation

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
    lat_direction: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=1,
        pattern='^[NSns]$'
    )
    lon_degrees: conint(ge=0, le=180)
    lon_minutes: conint(ge=0, le=59)
    lon_seconds: Optional[conint(ge=0, le=59)] = None
    lon_direction: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=1,
        pattern='^[EWew]$'
    )
    magnetic_variation: confloat(allow_inf_nan=False)


class UserWaypointReturn(WaypointBase):
    """
    This class defines the data-structure used to return user-waypoint data to the client.
    - name is optional.
    """

    id: conint(gt=0)
    name: Optional[constr(min_length=2, max_length=50)] = None
    created_at_utc: AwareDatetime
    last_updated_utc: AwareDatetime

    class Config():
        "Confirgaration parameters."
        from_attributes = True


class VfrWaypointReturn(UserWaypointReturn):
    """
    This class defines the data-structure used to return vfr-waypoint data to the client.
    """

    hidden: Optional[bool] = None


class UserWaypointData(WaypointBase):
    """
    This class defines the data-structure required form client to post user-waypoint data.
    It includes data validation.
    """

    @field_validator('magnetic_variation')
    @classmethod
    def round_magnetic_variation(cls, value: float) -> float:
        '''
        Classmethod to round magnetic_variation input value to 1 decimal place.

        Parameters:
        - value (float): the values to be validated.

        Returns:
        (float) : The magnetic_variation value rounded to 1 decimal place.

        '''
        return round(value, 1)

    @field_validator('name')
    @classmethod
    def clean_waypoint_name(cls, value: str) -> str:
        '''
        Classmethod to clean name string.

        Parameters:
        - value (str): the name string t to be validated.

        Returns:
        (str): cleaned name string.

        '''
        return None if value is None else clean_string(value)

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


class VfrWaypointData(UserWaypointData):
    """
    This class defines the data-structure required form client to post vfr-waypoint data.
    It includes data validation.
    """

    hidden: bool


class AerodromeBase(BaseModel):
    """
    This class defines the basic aerodrome data-structure
    """

    has_taf: bool
    has_metar: bool
    has_fds: bool
    elevation_ft: int


class RegisteredAerodromeData(VfrWaypointData, AerodromeBase):
    """
    This class defines the data required from client to post a new registered aerodrome.
    """
    status: int


class PrivateAerodromeData(UserWaypointData, AerodromeBase):
    """
    This class defines the data required from client to post a new private aerodrome.
    """
    status: int


class RegisteredAerodromeReturn(VfrWaypointReturn, AerodromeBase):
    """
    This class defines the registered-aerodrome data returned to the client.
    """
    status: str
    registered: bool


class PrivateAerodromeReturn(UserWaypointReturn, AerodromeBase):
    """
    This class defines the private-aerodrome data returned to the client.
    """
    status: str
    registered: bool


class RunwayInAerodromeReturn(BaseModel):
    """
    This class defines the runway  data-structure used to return to the client a list of runways,
    as part of the aerodrome data.
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
    This class defines the aerodrome data returned to the client, including the list of runways.
    """
    runways: Optional[conlist(item_type=RunwayInAerodromeReturn)] = []


class AerodromeStatusReturn(BaseModel):
    """
    This class defines the aerodrome-status data returned to the client.
    """
    id: int
    status: str
