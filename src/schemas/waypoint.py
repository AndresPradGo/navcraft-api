"""
Pydantic waypoint schemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema to validate data at the API endpoints.

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

from functions.data_processing import clean_string


class WaypointBase(BaseModel):
    """
    Schema that outlines the basic waypoint data required to create, edit or return waypoints
    """

    code: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=2,
        max_length=12,
        pattern="^['a-zA-Z0-9-]+$",
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
    magnetic_variation: Optional[confloat(
        allow_inf_nan=False, ge=-99.94, le=99.94)] = None


class UserWaypointReturn(WaypointBase):
    """
    Schema that outlines the user-waypoint data to return to the client
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
    Schema that outlines the vfr-waypoint data to return to the client
    """

    hidden: Optional[bool] = None


class UserWaypointData(WaypointBase):
    """
    Schema that outlines defines the data required to create a new user-waypoint
    """

    @field_validator('magnetic_variation')
    @classmethod
    def round_magnetic_variation(cls, value: float) -> float:
        """
        Classmethod to round magnetic_variation input value to 1 decimal place.
        """
        if value is None:
            return None
        return round(value, 2)

    @field_validator('name')
    @classmethod
    def clean_waypoint_name(cls, value: str) -> str:
        """
        Classmethod to clean name string.
        """
        return None if value is None else clean_string(value)

    @model_validator(mode='after')
    @classmethod
    def validate_waypoint_schema(cls, values):
        """
        Classmethod to check whether the lattitude is between 
        89 59 59 S and 90 0 0 N, and the longitude is between 
        179 59 59 W and 180 0 0 E; as part of the data validation.
        """

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
    Schema that outlines the data required to create a new vfr-waypoint
    """
    hidden: bool


class AerodromeBase(BaseModel):
    """
    Schema that outlines the basic aerodrome data required to create, edit or return aerodromes
    """
    elevation_ft: int


class RegisteredAerodromeData(VfrWaypointData, AerodromeBase):
    """
    Schema that outlines the data required create a new registered aerodrome
    """
    status: int
    has_taf: bool
    has_metar: bool
    has_fds: bool


class PrivateAerodromeData(UserWaypointData, AerodromeBase):
    """
    Schema that outlines the data required to create a new private aerodrome
    """
    status: int


class RegisteredAerodromeReturn(VfrWaypointReturn, AerodromeBase):
    """
    Schema that outlines the registered-aerodrome data to return to the client
    """
    status: str
    registered: bool
    has_taf: bool
    has_metar: bool
    has_fds: bool


class PrivateAerodromeReturn(UserWaypointReturn, AerodromeBase):
    """
    Schema that outlines the private-aerodrome data to return to the client
    """
    status: str
    registered: bool


class RunwayInAerodromeReturn(BaseModel):
    """
    Schema that outlines the runway data to return a list of 
    runways to the client, as part of the aerodrome data
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
    landing_length_ft: Optional[int] = None
    intersection_departure_length_ft: Optional[int] = None
    surface: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern="^[-a-zA-Z ']+$",
    )
    surface_id: int
    created_at_utc: AwareDatetime
    last_updated_utc: AwareDatetime

    @model_validator(mode='after')
    @classmethod
    def validate_runway_lengths(cls, values):
        """
        This function checks that landing length and intersection departure 
        length are less than or equal to total length. If landing lenth is 
        not provided, it will be equal to total length.
        """

        if values.landing_length_ft is None:
            values.landing_length_ft = values.length_ft
        elif values.landing_length_ft > values.length_ft:
            raise ValueError(
                "Landing length cannot be longer than total runway length.")

        if values.intersection_departure_length_ft is not None:
            if values.intersection_departure_length_ft > values.length_ft:
                raise ValueError(
                    "Intersection departure length cannot be longer than total runway length.")

        return values


class AerodromeReturnWithRunways(RegisteredAerodromeReturn):
    """
    Schema that outlines the aerodrome data to return to the 
    client, including the list of runways
    """
    runways: Optional[conlist(item_type=RunwayInAerodromeReturn)] = []


class AerodromeStatusReturn(BaseModel):
    """
    Schema that outlines the aerodrome-status data to return to the client
    """
    id: int
    status: str


class NearbyWaypointReturn(WaypointBase):
    """
    Schema that outlines the data to return to the client, a list of waypoints nearby a coordinate
    """
    id: int
    type: str
    distance: float
