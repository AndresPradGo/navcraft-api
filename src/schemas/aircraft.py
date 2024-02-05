"""
Pydantic aircraft schemas

This module defines the aircraft related pydantic schemas for data validation.

Usage: 
- Import the required schema to validate data at the API endpoints.

"""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, constr, conint, confloat, field_validator, model_validator, AwareDatetime

from functions.data_processing import clean_string


class FuelTypeData(BaseModel):
    """
    Schema that outlines the data required to create/edit a fuel type
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
        """
        Classmethod to round density_lb_gal input value to 2 decimal places.

        Parameters:
        - value (float): the density to be validated.

        Returns:
        (float): density value rounded to 2 decimal places.
        """
        return round(value, 2)


class FuelTypeReturn(FuelTypeData):
    """
    Schema that outlines the fuel type data to return to the client
    """

    id: conint(gt=0)


class PerformanceProfileData(BaseModel):
    """
    Schema that outlines the data reuired
    to create a new aircraft performance profile
    """
    fuel_type_id: conint(gt=0)
    performance_profile_name: constr(
        min_length=2,
        max_length=255,
        pattern="^[a-zA-Z0-9\s.,()/\-]+$"  # pylint: disable=anomalous-backslash-in-string
    )


class OfficialPerformanceProfileData(PerformanceProfileData):
    """
    Schema that outlines the data reuired
    to crate a new aircraft performance profile model
    """

    is_complete: bool


class PerformanceProfileReturn(OfficialPerformanceProfileData):
    """
    Schema that outlines the aircraft performance profile data to return to the client
    """

    id: conint(gt=0)
    center_of_gravity_in: Optional[confloat(ge=0, le=9999.94)] = None
    empty_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    max_ramp_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    max_takeoff_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    max_landing_weight_lb: Optional[confloat(ge=0, le=99999.94)] = None
    baggage_allowance_lb: Optional[confloat(ge=0, le=9999.94)] = None
    is_preferred: Optional[bool] = None
    created_at_utc: AwareDatetime
    last_updated_utc: AwareDatetime


class BaggageCompartmentData(BaseModel):
    """
    Schema that outlines the data required to create/edit an aircraft baggage compartment
    """

    name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    arm_in: confloat(ge=0, le=9999.94)
    weight_limit_lb: Optional[confloat(ge=0, le=9999.94)] = None

    @model_validator(mode='after')
    @classmethod
    def round_values_clean_name(cls, values: Dict[str, Any]) -> Dict:
        """
        Classmethod to round weight data and clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        """

        values.arm_in = round(values.arm_in, 2)
        values.weight_limit_lb = round(values.weight_limit_lb, 2)\
            if values.weight_limit_lb is not None else None
        values.name = clean_string(values.name)

        return values


class BaggageCompartmentReturn(BaggageCompartmentData):
    """
    Schema that outlines the aircraft baggage compartment data to return to the client
    """
    id: conint(gt=0)


class FuelTankData(BaseModel):
    """
    Schema that outlines the data required to create/edit an aircraft fuel tank
    """

    name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    arm_in: confloat(ge=0, le=9999.94)
    fuel_capacity_gallons: confloat(ge=0, le=999.94)
    unusable_fuel_gallons: Optional[confloat(ge=0, le=999.94)] = None
    burn_sequence: Optional[conint(ge=1)] = None

    @model_validator(mode='after')
    @classmethod
    def round_values_clean_name(cls, values: Dict[str, Any]) -> Dict:
        """
        Classmethod to round float data and clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        """

        values.arm_in = round(values.arm_in, 2)
        values.fuel_capacity_gallons = round(values.fuel_capacity_gallons, 2)
        values.unusable_fuel_gallons = round(values.unusable_fuel_gallons, 2)\
            if values.unusable_fuel_gallons is not None else None
        values.name = clean_string(values.name)

        return values


class FuelTankReturn(FuelTankData):
    """
    Schema that outlines the aircraft fuel tank data to return to the client
    """
    id: conint(gt=0)


class SeatRowData(BaggageCompartmentData):
    """
    Schema that outlines the data required to create/edit an aircraft seat row
    """

    number_of_seats: conint(ge=0)


class SeatRowReturn(SeatRowData):
    """
    Schema that outlines the aircraft seat row data to return to the client
    """
    id: conint(gt=0)


class AircraftArrangementReturn(BaseModel):
    """
    Schema that outlines the aircraft arrangement data to return to the client
    """
    baggage_compartments: Optional[List[BaggageCompartmentReturn]] = []
    seat_rows: Optional[List[SeatRowReturn]] = []
    fuel_tanks: Optional[List[FuelTankReturn]] = []


class PerformanceProfileWeightBalanceData(BaseModel):
    """
    Schema that outlines the data required to edit the weight and balance data,
    of an aircraft performance profile
    """
    center_of_gravity_in: confloat(ge=0, le=9999.94)
    empty_weight_lb: confloat(ge=0, le=99999.94)
    max_ramp_weight_lb: confloat(ge=0, le=99999.94)
    max_takeoff_weight_lb: confloat(ge=0, le=99999.94)
    max_landing_weight_lb: confloat(ge=0, le=99999.94)
    baggage_allowance_lb: confloat(ge=0, le=9999.94)

    @model_validator(mode='after')
    @classmethod
    def round_weight_and_cog(cls, values: Dict[str, Any]) -> Dict:
        """
        Classmethod to round weight data.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        """

        values.center_of_gravity_in = round(values.center_of_gravity_in, 2)
        values.empty_weight_lb = round(values.empty_weight_lb, 2)
        values.max_ramp_weight_lb = round(values.max_ramp_weight_lb, 2)
        values.max_landing_weight_lb = round(values.max_landing_weight_lb, 2)
        values.baggage_allowance_lb = round(values.baggage_allowance_lb, 2)
        return values


class AircraftData(BaseModel):
    """
    Schema that outlines the data required to create/edit an aircraft
    """

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
        """
        Classmethod to clean make.

        Parameters:
        - value (string): Make.

        Returns:
        - value (string): clean Make value.

        """
        return clean_string(value)


class AircraftReturn(AircraftData):
    """
    Schema that outlines the aircraft data to return to the client
    """

    id: conint(gt=0)
    created_at_utc: AwareDatetime
    last_updated_utc: AwareDatetime


class GetPerformanceProfileList(OfficialPerformanceProfileData):
    """
    Schema that outlines the aircraft performance profile data to return
    a list of aircraft performance profiles to the client
    """
    id: conint(gt=0)
    is_preferred: Optional[bool] = None
    created_at_utc: AwareDatetime
    last_updated_utc: AwareDatetime


class GetAircraftList(AircraftReturn):
    """
    Schema that outlines the aircraft data to return a list of aircraft to 
    the client
    """

    profiles: Optional[List[GetPerformanceProfileList]] = []


class WeightBalanceLimitData(BaseModel):
    """
    Schema that outlines the data required to create/edit a limit of a weight 
    and balance profile
    """

    cg_location_in: confloat(ge=0, le=9999.94)
    weight_lb: confloat(ge=0, le=99999.94)
    sequence: conint(ge=1)

    @model_validator(mode='after')
    @classmethod
    def round_values(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classmethod to round values.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        """

        values.cg_location_in = round(values.cg_location_in, 2)
        values.weight_lb = round(values.weight_lb, 2)

        return values


class WeightBalanceLimitReturn(WeightBalanceLimitData):
    """
    Schema that outlines the weight and balance profile limits' data to 
    return to the client
    """
    id: conint(gt=0)


class WeightBalanceData(BaseModel):
    """
    Schema that outlines the data required to crate/edit a weight and balance profile
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
        """
        Classmethod to clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        """
        return clean_string(value)


class WeightBalanceReturn(BaseModel):
    """
    Schema that outlines the weight and balance profile data to 
    return to the client
    """
    name: str
    id: conint(gt=0)
    limits: List[WeightBalanceLimitReturn] = []
    created_at_utc: AwareDatetime
    last_updated_utc: AwareDatetime


class GetWeightBalanceData(PerformanceProfileWeightBalanceData):
    """
    Schema that outlines all the weight and balance data of an aircraft 
    performance profile to return to the client
    """
    weight_balance_profiles: Optional[List[WeightBalanceReturn]] = []


class RunwaySurfacePercentIncrease(BaseModel):
    """
    Schema that outlines the data required to edit the takeoff/landing
    performance percentage increase, by runway surface
    """

    surface_id: conint(gt=0)
    percent: confloat(ge=0, le=99.94)

    @field_validator('percent')
    @classmethod
    def round_percentage(cls, value: float) -> float:
        """
        Classmethod to round percentages.

        Parameters:
        - value (float): percentage adjustment.

        Returns:
        (Dict): dictionary with the input values corrected.

        """
        return round(value, 2)


class RunwayDistanceAdjustmentPercentages(BaseModel):
    """
    Schema that outlines the takeoff/landing performance percentage 
    data to return to the client
    """

    percent_decrease_knot_headwind: Optional[confloat(ge=0, le=99.94)] = None
    percent_increase_knot_tailwind: Optional[confloat(ge=0, le=99.94)] = None
    percent_increase_runway_surfaces: Optional[
        List[RunwaySurfacePercentIncrease]
    ] = []

    @model_validator(mode='after')
    @classmethod
    def round_percentage_adjustments(cls, values: Dict[str, Any]) -> Dict:
        """
        Classmethod to round percentages.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        """

        if values.percent_decrease_knot_headwind is not None:
            values.percent_decrease_knot_headwind = round(
                values.percent_decrease_knot_headwind, 2)

        if values.percent_increase_knot_tailwind is not None:
            values.percent_increase_knot_tailwind = round(
                values.percent_increase_knot_tailwind, 2)

        return values


class TakeoffLandingPerformanceDataEntry(BaseModel):
    """
    Schema that outlines the data required to create an entry of
    an aircraft takeoff/landing performance table
    """

    weight_lb: conint(ge=0)
    pressure_alt_ft: conint(ge=0)
    temperature_c: int
    groundroll_ft: conint(ge=0)
    obstacle_clearance_ft: conint(ge=0)


class TakeoffLandingPerformanceReturn(RunwayDistanceAdjustmentPercentages):
    """
    Schema that outlines the takeoff/landing performance table data to return to the client
    """

    performance_data: List[TakeoffLandingPerformanceDataEntry]


class ClimbPerformanceAdjustments(BaseModel):
    """
    Schema that outlines the data required to edit the climb performance adjustmnet values
    """

    take_off_taxi_fuel_gallons: Optional[confloat(ge=0, le=99.94)] = None
    percent_increase_climb_temperature_c: Optional[confloat(
        ge=0, le=99.94)] = None

    @model_validator(mode='after')
    @classmethod
    def round_data(cls, values: Dict[str, Any]) -> Dict:
        """
        Classmethod to round percentages.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        """

        if values.take_off_taxi_fuel_gallons is not None:
            values.take_off_taxi_fuel_gallons = round(
                values.take_off_taxi_fuel_gallons, 2)

        if values.percent_increase_climb_temperature_c is not None:
            values.percent_increase_climb_temperature_c = round(
                values.percent_increase_climb_temperature_c, 2)

        return values


class ClimbPerformanceDataEntry(BaseModel):
    """
    Schema that outlines the data required to create an entry of
    an aircraft climb performance table
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
        """
        Classmethod to round fuel burn.

        Parameters:
        - value (float): fuel burn.

        Returns:
        (float): rounded fuel burn.

        """
        return round(value, 2)


class ClimbPerformanceReturn(ClimbPerformanceAdjustments):
    """
    Schema that outlines the climb performance table data to return to the client
    """

    performance_data: List[ClimbPerformanceDataEntry]


class CruisePerformanceDataEntry(BaseModel):
    """
    Schema that outlines the data required to create an entry of
    an aircraft cruise performance table
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
        """
        Classmethod to round fuel burn.

        Parameters:
        - value (float): fuel burn.

        Returns:
        (float): rounded fuel burn.

        """
        return round(value, 2)


class CruisePerformanceReturn(BaseModel):
    """
    Schema that outlines the cruise performance table data to return to the client
    """

    performance_data: List[CruisePerformanceDataEntry]
