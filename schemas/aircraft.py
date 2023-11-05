"""
Pydantic aircraft schemas

This module defines the aircraft related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, constr, conint, confloat, field_validator, model_validator

from functions.data_processing import clean_string


class FuelTypeData(BaseModel):
    """
    This class defines the data-structure required from client to post fuel type data.
    """

    name: constr(
        min_length=1,
        max_length=50,
        pattern="^[-a-zA-Z0-9 /]+$"
    )
    density_lb_gal: confloat(gt=0, le=99.94, allow_inf_nan=False)

    @field_validator('density_lb_gal')
    @classmethod
    def round_density(cls, value: float) -> float:
        '''
        Classmethod to round density_lb_gal input value to 2 decimal places.

        Parameters:
        - value (float): the density to be validated.

        Returns:
        (float): density value rounded to 2 decimal places.
        '''
        return round(value, 2)


class FuelTypeReturn(FuelTypeData):
    """
    This class defines the data-structure required to return fuel type data to the client.
    """

    id: conint(gt=0)


class PerformanceProfileData(BaseModel):
    '''
    This class defines the data structure reuired from the client, in order to add
    a new performance profile to the database.
    '''
    fuel_type_id: conint(gt=0)
    performance_profile_name: constr(
        min_length=2,
        max_length=255,
        pattern="^[\-a-zA-Z0-9, ]+$"  # pylint: disable=anomalous-backslash-in-string
    )


class OfficialPerformanceProfileData(PerformanceProfileData):
    '''
    This class defines the data structure reuired from the client, in order to add
    an official performance profile to the database.
    '''

    is_complete: bool


class PerformanceProfileReturn(OfficialPerformanceProfileData):
    """
    This class defines the data-structure required to return performance profile data
    to the client.
    """

    id: conint(gt=0)
    center_of_gravity_in: Optional[confloat(ge=0, le=999.94)] = None
    empty_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    max_ramp_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    max_takeoff_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    max_landing_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    baggage_allowance_lb: Optional[confloat(ge=0, le=9999.94)] = None
    is_preferred: Optional[bool] = None


class BaggageCompartmentData(BaseModel):
    '''
    This class defines the baggage compartment data structure.
    '''

    name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    arm_in: confloat(ge=0, le=999.94)
    weight_limit_lb: Optional[confloat(ge=0, le=9999.94)] = None

    @model_validator(mode='after')
    @classmethod
    def round_values_clean_name(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round weight data and clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values.arm_in = round(values.arm_in, 2)
        values.weight_limit_lb = round(values.weight_limit_lb, 2)\
            if values.weight_limit_lb is not None else None
        values.name = clean_string(values.name)

        return values


class BaggageCompartmentReturn(BaggageCompartmentData):
    '''
    This class defines the baggage compartment data structure to be returned to the client.
    '''
    id: conint(gt=0)


class FuelTankData(BaseModel):
    '''
    This class defines the fuel tank data required to post a new fuel tank.
    '''

    name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    arm_in: confloat(ge=0, le=999.94)
    fuel_capacity_gallons: confloat(ge=0, le=999.94)
    unusable_fuel_gallons: Optional[confloat(ge=0, le=999.94)] = None
    burn_sequence: Optional[conint(ge=1)] = None

    @model_validator(mode='after')
    @classmethod
    def round_values_clean_name(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round float data and clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values.arm_in = round(values.arm_in, 2)
        values.fuel_capacity_gallons = round(values.fuel_capacity_gallons, 2)
        values.unusable_fuel_gallons = round(values.unusable_fuel_gallons, 2)\
            if values.unusable_fuel_gallons is not None else None
        values.name = clean_string(values.name)

        return values


class FuelTankReturn(FuelTankData):
    '''
    This class defines the fuel tank data structure to be returned to the client.
    '''
    id: conint(gt=0)


class SeatRowData(BaggageCompartmentData):
    '''
    This class defines the seat row data structure.
    '''

    number_of_seats: conint(ge=0)


class SeatRowReturn(SeatRowData):
    '''
    This class defines the seat row data structure to be returned to the client.
    '''
    id: conint(gt=0)


class PerformanceProfileWeightBalanceData(BaseModel):
    '''
    This class defines the data structure reuired from the client, in order to add
    weight and balance data to a performance profile.
    '''
    center_of_gravity_in: confloat(ge=0, le=999.94)
    empty_weight_lb: confloat(ge=0, le=99999.94)
    max_ramp_weight_lb: confloat(ge=0, le=99999.94)
    max_takeoff_weight_lb: confloat(ge=0, le=99999.94)
    max_landing_weight_lb: confloat(ge=0, le=99999.94)
    baggage_allowance_lb: confloat(ge=0, le=9999.94)

    @model_validator(mode='after')
    @classmethod
    def round_weight_and_cog(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round weight data.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values.center_of_gravity_in = round(values.center_of_gravity_in, 2)
        values.empty_weight_lb = round(values.empty_weight_lb, 2)
        values.max_ramp_weight_lb = round(values.max_ramp_weight_lb, 2)
        values.max_landing_weight_lb = round(values.max_landing_weight_lb, 2)
        values.baggage_allowance_lb = round(values.baggage_allowance_lb, 2)
        return values


class AircraftData(BaseModel):
    '''
    This class defines the data required form the client to edit an aircraft.
    '''

    make: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern="^[\.\-a-zA-Z0-9\(\) ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    model: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern="^[\.\-a-zA-Z0-9\(\) ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    abbreviation: constr(
        to_upper=True,
        strip_whitespace=True,
        min_length=2,
        max_length=10,
        pattern="^[\-a-zA-Z0-9]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    registration: constr(
        to_upper=True,
        strip_whitespace=True,
        min_length=2,
        max_length=10,
        pattern="^[\-a-zA-Z0-9]+$"  # pylint: disable=anomalous-backslash-in-string
    )

    @field_validator('make')
    @classmethod
    def clean_make(cls, value: str) -> str:
        '''
        Classmethod to clean make.

        Parameters:
        - value (string): Make.

        Returns:
        - value (string): clean Make value.

        '''
        return clean_string(value)


class AircraftReturn(AircraftData):
    """
    This class defines the base data-structure required to return aircraft data
    to the client.
    """

    id: conint(gt=0)


class GetPerformanceProfileList(OfficialPerformanceProfileData):
    """
    This class defines the data-structure required to return 
    a list of performance profiles to the client.
    """
    id: conint(gt=0)
    is_preferred: Optional[bool] = None


class GetAircraftList(AircraftReturn):
    """
    This class defines the data-structure required to return 
    a list of aircraft to the client.
    """

    profiles: Optional[List[GetPerformanceProfileList]] = []


class WeightBalanceLimitData(BaseModel):
    """
    This class defines the data-structure required to post weight and balance limits of a 
    weight and balance profile.
    """

    cg_location_in: confloat(ge=0, le=999.94)
    weight_lb: confloat(ge=0, le=99999.94)
    sequence: conint(ge=1)

    @model_validator(mode='after')
    @classmethod
    def round_values(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Classmethod to round values.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values.cg_location_in = round(values.cg_location_in, 2)
        values.weight_lb = round(values.weight_lb, 2)

        return values


class WeightBalanceLimitReturn(WeightBalanceLimitData):
    """
    This class defines the data-structure required to return weight and balance limits of a 
    weight and balance profile.
    """
    id: conint(gt=0)


class WeightBalanceData(BaseModel):
    """
    This class defines the data-structure required to post a weight and balance profile.
    """

    name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9\(\) ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    limits: List[WeightBalanceLimitData] = []

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str) -> str:
        '''
        Classmethod to clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''
        return clean_string(value)


class WeightBalanceReturn(WeightBalanceData):
    """
    This class defines the data-structure required to return a weight and balance profile.
    """

    id: conint(gt=0)
    limits: List[WeightBalanceLimitReturn] = []


class GetWeightBalanceData(PerformanceProfileWeightBalanceData):
    """
    This class defines the data-structure required to return all the weight 
    and balance data from a performance profile.
    """
    baggage_compartments: Optional[List[BaggageCompartmentReturn]] = []
    seat_rows: Optional[List[SeatRowReturn]] = []
    fuel_tanks: Optional[List[FuelTankReturn]] = []
    weight_balance_profiles: Optional[List[WeightBalanceReturn]] = []


class RunwaySurfacePercentIncrease(BaseModel):
    '''
    This class defines the percentage increase by runway surface data structure.
    '''

    surface_id: conint(gt=0)
    percent: confloat(ge=0, le=99.94)

    @field_validator('percent')
    @classmethod
    def round_percentage(cls, value: float) -> float:
        '''
        Classmethod to round percentages.

        Parameters:
        - value (float): percentage adjustment.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''
        return round(value, 2)


class RunwayDistanceAdjustmentPercentages(BaseModel):
    '''
    This class defines the data structure to return runway distance 
    adjustment percentages to the client.
    '''

    percent_decrease_knot_headwind: Optional[confloat(ge=0, le=99.94)] = None
    percent_increase_knot_tailwind: Optional[confloat(ge=0, le=99.94)] = None
    percent_increase_runway_surfaces: Optional[
        List[RunwaySurfacePercentIncrease]
    ] = []

    @model_validator(mode='after')
    @classmethod
    def round_percentage_adjustments(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round percentages.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        if values.percent_decrease_knot_headwind is not None:
            values.percent_decrease_knot_headwind = round(
                values.percent_decrease_knot_headwind, 2)

        if values.percent_increase_knot_tailwind is not None:
            values.percent_increase_knot_tailwind = round(
                values.percent_increase_knot_tailwind, 2)

        return values


class TakeoffLandingPerformanceDataEntry(BaseModel):
    """
    This class defines the data structure for takeoff/landing performance data entries.
    """

    weight_lb: conint(ge=0)
    pressure_alt_ft: conint(ge=0)
    temperature_c: int
    groundroll_ft: conint(ge=0)
    obstacle_clearance_ft: conint(ge=0)


class TakeoffLandingPerformanceReturn(RunwayDistanceAdjustmentPercentages):
    '''
    This class defines the data structure to return takeoff/landing 
    performance data to the client.
    '''

    performance_data: List[TakeoffLandingPerformanceDataEntry]


class ClimbPerformanceAdjustments(BaseModel):
    '''
    This class defines the data structure of climb adjustment data.
    '''

    take_off_taxi_fuel_gallons: Optional[confloat(ge=0, le=99.94)] = None
    percent_increase_climb_temperature_c: Optional[confloat(
        ge=0, le=99.94)] = None

    @model_validator(mode='after')
    @classmethod
    def round_data(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round percentages.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        if values.take_off_taxi_fuel_gallons is not None:
            values.take_off_taxi_fuel_gallons = round(
                values.take_off_taxi_fuel_gallons, 2)

        if values.percent_increase_climb_temperature_c is not None:
            values.percent_increase_climb_temperature_c = round(
                values.percent_increase_climb_temperature_c, 2)

        return values


class ClimbPerformanceDataEntry(BaseModel):
    """
    This class defines the data structure for climb performance data entries.
    """

    weight_lb: conint(ge=0)
    pressure_alt_ft: conint(ge=0)
    temperature_c: int
    kias: Optional[conint(ge=0)] = None
    fpm: Optional[conint(ge=0)] = None
    time_min: conint(ge=0)
    fuel_gal: confloat(ge=0, le=99.94)
    distance_nm: conint(ge=0)

    @field_validator('fuel_gal')
    @classmethod
    def round_percentage_adjustments(cls, value: float) -> float:
        '''
        Classmethod to round fuel burn.

        Parameters:
        - value (float): fuel burn.

        Returns:
        (float): rounded fuel burn.

        '''
        return round(value, 2)


class ClimbPerformanceReturn(ClimbPerformanceAdjustments):
    '''
    This class defines the data structure to return climb 
    performance data to the client.
    '''

    performance_data: List[ClimbPerformanceDataEntry]


class CruisePerformanceDataEntry(BaseModel):
    """
    This class defines the data structure for cruise performance data entries.
    """

    weight_lb: conint(ge=0)
    pressure_alt_ft: conint(ge=0)
    temperature_c: int
    bhp_percent: conint(ge=0)
    gph: confloat(ge=0, le=9999.94)
    rpm: conint(ge=0)
    ktas: conint(ge=0)

    @field_validator('gph')
    @classmethod
    def round_percentage_adjustments(cls, value: float) -> float:
        '''
        Classmethod to round fuel burn.

        Parameters:
        - value (float): fuel burn.

        Returns:
        (float): rounded fuel burn.

        '''
        return round(value, 2)


class CruisePerformanceReturn(BaseModel):
    '''
    This class defines the data structure to return cruise 
    performance data to the client.
    '''

    performance_data: List[CruisePerformanceDataEntry]
