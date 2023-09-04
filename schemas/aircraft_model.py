"""
Pydantic aircraft schemas

This module defines the aircraft related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, constr, conint, confloat, field_validator, model_validator

from utils.functions import clean_string


class AircraftMakeData(BaseModel):
    '''
    This class defines the data-structure required from client to post a new aircraft manufacturer.
    '''

    name: constr(
        to_upper=True,
        min_length=2,
        max_length=255,
        pattern="^[\.\-a-zA-Z0-9\(\) ]+$"  # pylint: disable=anomalous-backslash-in-string
    )

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str) -> str:
        '''
        Classmethod to clean name string.

        Parameters:
        - value (str): the name string to be validated.

        Returns:
        (str): cleaned name string.
        '''
        return clean_string(value)


class AircraftMakeReturn(AircraftMakeData):
    """
    This class defines the data-structure required to return aircraft manufacturer data to the client.
    """

    id: conint(gt=0)


class FuelTypeData(BaseModel):
    """
    This class defines the data-structure required from client to post fuel type data.
    """

    name: constr(
        min_length=1,
        max_length=50,
        pattern="^[-a-zA-Z0-9 /]+$"
    )
    density_lb_gal: confloat(gt=0, allow_inf_nan=False)

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

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str) -> str:
        '''
        Classmethod to clean name string.

        Parameters:
        - value (str): the name string to be validated.

        Returns:
        (str): cleaned name string.
        '''
        return clean_string(value)


class FuelTypeReturn(FuelTypeData):
    """
    This class defines the data-structure required to return fuel type data to the client.
    """

    id: conint(gt=0)


class PerformanceProfilePostData(BaseModel):
    '''
    This class defines the data structure reuired from the client, in order to add
    a new performance profile to the database
    '''
    fuel_type_id: conint(gt=0)
    performance_profile_name: constr(
        min_length=2,
        max_length=255,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    is_complete: Optional[bool] = None

    @field_validator("performance_profile_name")
    @classmethod
    def clean_performance_profile_name(cls, value: str) -> str:
        '''
        Classmethod to clean profile name.

        Parameters:
        - values (str): profile name.

        Returns:
        (str): profile name.

        '''

        return clean_string(value)


class BaggageCompartmentData(BaseModel):
    '''
    This class defines the baggage compartment data structure.
    '''

    name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    arm_in: confloat(ge=0)
    weight_limit_lb: Optional[confloat(ge=0)] = None

    @model_validator(mode='before')
    @classmethod
    def round_values_clean_name(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round weight data and clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values["arm_in"] = round(values["arm_in"], 2)
        if "weight_limit_lb" in values:
            values["weight_limit_lb"] = round(values["weight_limit_lb"], 2)\
                if values["weight_limit_lb"] is not None else None
        values["name"] = clean_string(values["name"])

        return values


class BaggageCompartmentReturn(BaggageCompartmentData):
    '''
    This class defines the baggage compartment data structure to be returned to the client.
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


class PerformanceProfileWightBalanceData(BaseModel):
    '''
    This class defines the data structure reuired from the client, in order to add
    weight and balance data to a performance profile.
    '''
    center_of_gravity_in: confloat(ge=0)
    empty_weight_lb: confloat(ge=0)
    max_ramp_weight_lb: confloat(ge=0)
    max_landing_weight_lb: confloat(ge=0)
    fuel_arm_in: confloat(ge=0)
    fuel_capacity_gallons: confloat(ge=0)

    @model_validator(mode='before')
    @classmethod
    def round_weight_and_cog(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round weight data.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values["center_of_gravity_in"] = round(
            values["center_of_gravity_in"], 2)
        values["empty_weight_lb"] = round(values["empty_weight_lb"], 2)
        values["max_ramp_weight_lb"] = round(values["max_ramp_weight_lb"], 2)
        values["max_landing_weight_lb"] = round(
            values["max_landing_weight_lb"], 2)
        values["fuel_arm_in"] = round(values["fuel_arm_in"], 2)
        values["fuel_capacity_gallons"] = round(
            values["fuel_capacity_gallons"], 2)
        return values


class PerformanceProfilePostReturn(PerformanceProfilePostData):
    """
    This class defines the data-structure required to return performance profile data
    to the client.
    """

    id: conint(gt=0)
    center_of_gravity_in: Optional[confloat(ge=0)] = None
    empty_weight_lb: Optional[confloat(ge=0)] = None
    max_ramp_weight_lb: Optional[confloat(ge=0)] = None
    max_landing_weight_lb: Optional[confloat(ge=0)] = None
    fuel_arm_in: Optional[confloat(ge=0)] = None
    fuel_capacity_gallons: Optional[confloat(ge=0)] = None


class AircraftModelOfficialBaseData(BaseModel):
    '''
    This class defines the base data structure reuired from the client, in order to edit
    a official aircraft models.
    '''

    make_id: conint(gt=0)
    model: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=255,
        pattern="^[\.\-a-zA-Z0-9\(\) ]+$"  # pylint: disable=anomalous-backslash-in-string
    )
    code: constr(
        to_upper=True,
        strip_whitespace=True,
        min_length=2,
        max_length=5,
        pattern="^[\-a-zA-Z0-9]+$"  # pylint: disable=anomalous-backslash-in-string
    )


class AircraftModelOfficialPostData(AircraftModelOfficialBaseData, PerformanceProfilePostData):
    '''
    This class defines the data structure reuired from the client, in order to add
    a new official aircraft model to the database as an admin user.
    '''


class AircraftModelOfficialBaseReturn(AircraftModelOfficialBaseData):
    """
    This class defines the base data-structure required to return Official aircraft model data
    to the client.
    """

    id: conint(gt=0)


class AircraftModelOfficialPostReturn(AircraftModelOfficialBaseReturn, PerformanceProfilePostData):
    """
    This class defines the data-structure required to return Official aircraft model data
    to the client.
    """

    performance_profile_id: conint(gt=0)


class WeightBalanceLimitData(BaseModel):
    """
    This class defines the data-structure required to post weight and balance limits of a 
    weight and balance profile.
    """

    from_cg_in: confloat(ge=0)
    from_weight_lb: confloat(ge=0)
    to_cg_in: confloat(ge=0)
    to_weight_lb: confloat(ge=0)

    @model_validator(mode='before')
    @classmethod
    def round_values(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Classmethod to round values.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values["from_cg_in"] = round(values["from_cg_in"], 2)
        values["from_weight_lb"] = round(values["from_weight_lb"], 2)
        values["to_cg_in"] = round(values["to_cg_in"], 2)
        values["to_weight_lb"] = round(values["to_weight_lb"], 2)
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
    max_take_off_weight_lb: confloat(ge=0)
    limits: List[WeightBalanceLimitData] = []

    @model_validator(mode='before')
    @classmethod
    def round_values_clean_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Classmethod to round weight data and clean name.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        values["max_take_off_weight_lb"] = round(
            values["max_take_off_weight_lb"], 2)
        values["name"] = clean_string(values["name"])

        return values


class WeightBalanceReturn(WeightBalanceData):
    """
    This class defines the data-structure required to return a weight and balance profile.
    """

    id: conint(gt=0)
    limits: List[WeightBalanceLimitReturn] = []


class RunwaySurfacePercentIncrease(BaseModel):
    '''
    This class defines the percentage increase by runway surface data structure.
    '''

    surface_id: conint(gt=0)
    percent: confloat(ge=0)

    model_validator(mode='before')

    @classmethod
    def round_percentage_adjustments(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round percentages.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''
        values["percent"] = round(values["percent"], 2)
        return values


class RunwayDistanceAdjustmentPercentages(BaseModel):
    '''
    This class defines the data structure to return runway distance 
    adjustment percentages to the client.
    '''

    id: conint(gt=0)
    percent_decrease_knot_headwind: Optional[confloat(ge=0)] = None
    percent_increase_knot_tailwind: Optional[confloat(ge=0)] = None
    percent_increase_runway_surfaces: Optional[
        List[RunwaySurfacePercentIncrease]
    ] = []

    @model_validator(mode='before')
    @classmethod
    def round_percentage_adjustments(cls, values: Dict[str, Any]) -> Dict:
        '''
        Classmethod to round percentages.

        Parameters:
        - values (Dict): dictionary with the input values.

        Returns:
        (Dict): dictionary with the input values corrected.

        '''

        if "percent_decrease_knot_headwind" in values\
                and values["percent_decrease_knot_headwind"] is not None:
            values["percent_decrease_knot_headwind"] = round(
                values["percent_decrease_knot_headwind"], 2)
        else:
            values["percent_decrease_knot_headwind"] = None

        if "percent_increase_knot_tailwind" in values\
                and values["percent_increase_knot_tailwind"] is not None:
            values["percent_increase_knot_tailwind"] = round(
                values["percent_increase_knot_tailwind"], 2)
        else:
            values["percent_increase_knot_tailwind"] = None

        return values
