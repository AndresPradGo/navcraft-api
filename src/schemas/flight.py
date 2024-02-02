"""
Pydantic flight schemas

This module defines the flight related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.
"""

from typing import List, Optional

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
        pattern="^[-A-Za-z0-9']+$",
    )
    name: constr(min_length=2, max_length=255)
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
    magnetic_variation: Optional[confloat(
        allow_inf_nan=False, ge=-99.94, le=99.94)] = None

    @field_validator('magnetic_variation')
    @classmethod
    def round_magnetic_variation(cls, value: float) -> float | None:
        '''
        Classmethod to round magnetic_variation input value to 1 decimal place.

        Parameters:
        - value (float): the values to be validated.

        Returns:
        (float) : The magnetic_variation value rounded to 2 decimal place.

        '''
        if value is not None:
            return round(value, 2)

        return None

    @model_validator(mode='after')
    @classmethod
    def validate_waypoint_schema(cls, values):
        '''
        Classmethod to check whether the lattitude is between 
        89 59 59 S and 90 0 0 N, and the longitude is between 
        179 59 59 W and 180 0 0 E; as part of the data validation.

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
    from_user_waypoint: bool
    from_vfr_waypoint: bool


class LegWaypointData(BaseModel):
    """
    This class defines the data required to add or edit a flight-leg's waypoint.
    """
    new_waypoint: Optional[NewFlightWaypointData] = None
    existing_waypoint_id: Optional[conint(ge=0)] = None


class NewLegData(LegWaypointData):
    """
    This class defines the data required to post new flight-legs.
    """
    sequence: conint(ge=1)

    @model_validator(mode='after')
    @classmethod
    def validate_waypoint_schema(cls, values):
        '''
        Classmethod to check that only new_waypoint or existing_waypoint_id are provided.
        '''
        if values.existing_waypoint_id is None and values.new_waypoint is None:
            raise ValueError(
                "Please provide waypoint data, or a valid waypoint id.")
        if values.existing_waypoint_id is not None and values.new_waypoint is not None:
            raise ValueError(
                "Please provide only waypoint data, or a valid waypoint id.")

        return values


class LegWeatherData(BaseModel):
    """
    This class defines the data required to update flight-legs weather data.
    """
    temperature_c: int
    altimeter_inhg: confloat(ge=-99.94, le=99.94)
    wind_direction: Optional[conint(ge=0, le=360)] = None
    wind_magnitude_knot: conint(ge=0)
    temperature_last_updated: Optional[AwareDatetime] = None
    wind_last_updated: Optional[AwareDatetime] = None
    altimeter_last_updated: Optional[AwareDatetime] = None

    @field_validator('altimeter_inhg')
    @classmethod
    def round_altimeter_inhg(cls, value: float) -> float | None:
        '''
        Classmethod to round altimeter_inhg input value to 2 decimal place.
        '''
        return round(value, 2)

    @model_validator(mode='after')
    @classmethod
    def validate_wind_data(cls, values):
        '''
        Classmethod to check that wind direction is provided, if wind magnitud is not zero.
        '''

        if values.wind_magnitude_knot > 0 and values.wind_direction is None:
            raise ValueError(
                "Please provide wind direction."
            )
        elif values.wind_magnitude_knot == 0 and values.wind_direction is not None:
            values.wind_direction = None

        return values


class BaseWeatherReportRequestData(BaseModel):
    """
    This class defines the aerodrome data required by the client, to get weather data 
    reports from nerby aerodromes, for flight planing and briefing purposes.
    """
    code: str
    distance_from_target_nm: int


class NewLegReturn(LegWeatherData):
    """
    This class defines the data returned to the client, after posting new flight-legs.
    """
    id: conint(ge=0)
    sequence: conint(ge=1)
    waypoint: Optional[NewFlightWaypointReturn] = None
    altitude_ft: conint(ge=500)
    upper_wind_aerodromes: List[BaseWeatherReportRequestData] = []
    metar_aerodromes: List[BaseWeatherReportRequestData] = []
    briefing_aerodromes: List[BaseWeatherReportRequestData] = []


class UpdateLegData(LegWeatherData, LegWaypointData):
    """
    This class defines the data required from the client to update a leg data.
    """
    altitude_ft: conint(ge=500, lt=18000)

    @model_validator(mode='after')
    @classmethod
    def validate_waypoint_schema(cls, values):
        '''
        Classmethod to check that only new_waypoint or existing_waypoint_id are provided.
        '''

        if values.existing_waypoint_id is not None and values.new_waypoint is not None:
            raise ValueError(
                "Please provide only waypoint data, or a valid waypoint id.")

        return values


class NewFlightData(BaseModel):
    """
    This class defines the flight data requiered to post a new flight.
    """
    departure_time: AwareDatetime
    aircraft_id: Optional[conint(gt=0)] = None
    departure_aerodrome_id: Optional[conint(gt=0)] = None
    arrival_aerodrome_id: Optional[conint(gt=0)] = None


class UpdateFlightData(BaseModel):
    """
    This class defines the data required from the 
    client to update the general flight data.
    """
    departure_time: AwareDatetime
    bhp_percent: conint(ge=20, le=100)
    added_enroute_time_hours: confloat(allow_inf_nan=False, ge=0, le=99.94)
    reserve_fuel_hours: confloat(allow_inf_nan=False, ge=0, le=99.94)
    contingency_fuel_hours: confloat(allow_inf_nan=False, ge=0, le=99.94)
    briefing_radius_nm: conint(ge=5, le=20)
    alternate_radius_nm: conint(ge=5, le=100)

    @model_validator(mode='after')
    @classmethod
    def round_fuel(cls, values):
        '''
        Classmethod to round the fuel values.
        '''
        values.added_enroute_time_hours = round(
            values.added_enroute_time_hours, 2)
        values.reserve_fuel_hours = round(values.reserve_fuel_hours, 2)
        values.contingency_fuel_hours = round(values.contingency_fuel_hours, 2)

        return values


class NewFlightReturn(NewFlightData):
    """
    This class defines the flight data returned to the client after posting a new flight.
    """
    id: conint(gt=0)
    departure_aerodrome_is_private: Optional[bool] = None
    arrival_aerodrome_is_private: Optional[bool] = None
    waypoints: List[str] = []


class ExtensiveFlightDataReturn(NewFlightData, UpdateFlightData):
    """
    This class defines the data returned to the client, for a detailed flight observation.
    """
    id: conint(gt=0)
    departure_aerodrome_is_private: Optional[bool] = None
    departure_taf_aerodromes: List[BaseWeatherReportRequestData] = []
    departure_metar_aerodromes: List[BaseWeatherReportRequestData] = []
    departure_weather: LegWeatherData
    arrival_aerodrome_is_private: Optional[bool] = None
    arrival_taf_aerodromes: List[BaseWeatherReportRequestData] = []
    arrival_metar_aerodromes: List[BaseWeatherReportRequestData] = []
    arrival_weather: LegWeatherData
    legs: List[NewLegReturn] = []
    briefing_radius_nm: conint(ge=0)
    alternate_radius_nm: conint(ge=0)
    all_weather_is_official: bool
    weather_hours_from_etd: conint(ge=-1)
    alternates: List[BaseWeatherReportRequestData] = []


class UpdateDepartureArrivalData(BaseModel):
    """
    This class defines the data required from the 
    client to update the departure and arrival flight data.
    """
    aerodrome_id: conint(gt=0)
    wind_direction: Optional[conint(gt=0, le=360)] = None
    wind_magnitude_knot: conint(ge=0)
    temperature_c: int
    altimeter_inhg: confloat(ge=-99.94, le=99.94)
    temperature_last_updated: Optional[AwareDatetime] = None
    wind_last_updated: Optional[AwareDatetime] = None
    altimeter_last_updated: Optional[AwareDatetime] = None

    @model_validator(mode='after')
    @classmethod
    def validate_wind_data(cls, values):
        '''
        Classmethod to check that wind direction is provided, if wind magnitud is not zero.
        '''

        if values.wind_magnitude_knot > 0 and values.wind_direction is None:
            raise ValueError(
                "Please provide wind direction."
            )
        elif values.wind_magnitude_knot == 0 and values.wind_direction is not None:
            values.wind_direction = None

        return values

    @field_validator('altimeter_inhg')
    @classmethod
    def round_altimeter_inhg(cls, value: float) -> float | None:
        '''
        Classmethod to round altimeter_inhg input value to 2 decimal place.
        '''
        return round(value, 2)


class WaypointsNotUpdatedReturn(BaseModel):
    """
    This class defined the basic data returned to the client, 
    to show a list of flight waypoints that could not be updated.
    """
    waypoint_id: conint(gt=0)
    code: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=2,
        max_length=50,
        pattern="^['-a-zA-Z0-9]+$",
    )


class UpdateWaypointsReturn(BaseModel):
    """
    This class defines the data returned to the user, after updating a flight's
    waypoints.
    """

    flight_data: ExtensiveFlightDataReturn
    user_waypoints_not_found: List[WaypointsNotUpdatedReturn]
    vfr_waypoints_not_found: List[WaypointsNotUpdatedReturn]
