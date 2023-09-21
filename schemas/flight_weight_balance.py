"""
Pydantic flight weight and balance schemas

This module defines the flight weight and balance related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional, List

from pydantic import (
    BaseModel,
    conint,
    constr,
    confloat,
    model_validator
)

from functions.data_processing import clean_string


class PersonOnBoardData(BaseModel):
    """"
    This class defines the data structure required to add a new person on board.
    """

    seat_row_id: conint(gt=0)
    name: Optional[constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9' ]+$",
    )] = None
    weight_lb: Optional[confloat(allow_inf_nan=False, ge=0, le=999.99)] = None
    is_me: Optional[bool] = None
    passenger_profile_id: Optional[conint(gt=0)] = None

    @model_validator(mode='after')
    @classmethod
    def validate_data_source(cls, values):
        '''
        Classmethod to check that only 1 out of 3 possible data sources is provided.

        Parameters:
        - values (Any): The object with the values to be validated.

        Returns:
        (Any) : The object of validated values.

        Raises:
        ValueError: if more or less than 1 source of weight data is provided.

        '''

        value_list = [values.weight_lb, values.is_me,
                      values.passenger_profile_id]
        count_not_none_values = sum(
            [1 for values in value_list if values is not None])

        if count_not_none_values < 1:
            raise ValueError(
                "for every person on boars, please provide a source of weight value.")
        if count_not_none_values > 1:
            raise ValueError(
                "Please provide only one source of passenger/crew-member weight.")
        if values.weight_lb is not None:
            if values.name is None:
                raise ValueError(
                    "Please provide a name for all persons on board.")
            values.weight_lb = round(values.weight_lb, 2)
            values.name = clean_string(values.name)

        return values


class PersonOnBoardReturn(BaseModel):
    """"
    This class defines the data structure required to return 
    person on board data to the client.
    """
    id: conint(gt=0)
    seat_row_id: conint(gt=0)
    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9' ]+$",
    )
    weight_lb: confloat(allow_inf_nan=False, ge=0, le=999.99)
    user_id: Optional[conint(gt=0)] = None
    passenger_profile_id: Optional[conint(gt=0)] = None


class FlightBaggageData(BaseModel):
    """"
    This class defines the data structure required to add a new baggage.
    """

    baggage_compartment_id: conint(gt=0)
    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9' ]+$",
    )
    weight_lb: confloat(allow_inf_nan=False, ge=0, le=999.99)

    @model_validator(mode='after')
    @classmethod
    def round_weight_and_clean_name(cls, values):
        '''
        Classmethod to round the weight and clean name string.

        Parameters:
        - values (Any): input values.

        Returns:
        (Any): input values with rounded weight and clean name.
        '''
        values.weight_lb = round(values.weight_lb, 2)
        values.name = clean_string(values.name)

        return values


class FlightBaggageReturn(FlightBaggageData):
    """"
    This class defines the data structure required to return baggage data to the client.
    """
    id: conint(gt=0)


class FlightFuelReturn(BaseModel):
    """"
    This class defines the data structure required to return fuel data to the client.
    """
    id: conint(gt=0)
    fuel_tank_id: conint(gt=0)
    gallons: confloat(allow_inf_nan=False, ge=0, le=999.99)


class BaseWeightAndBalanceReportReturn(BaseModel):
    """
    This class defines the base weight and balance data 
    returned to the client in the  W&B report.
    """

    weight_lb: float
    arm_in: float
    moment_lb_in: float


class WeightAndBalanceFuelReturn(BaseWeightAndBalanceReportReturn):
    """
    This class defines the data structure to return fuel 
    weight and balance data to the client, as pasrt of the W&B report.
    """

    gallons: confloat(allow_inf_nan=False, ge=0, le=999.99)


class WeightAndBalanceFuelTankReturn(WeightAndBalanceFuelReturn):
    """
    This class defines the data structure to return fuel 
    weight and balance data to the client, as pasrt of the W&B report.
    """

    fuel_tank_id: conint(gt=0)
    fuel_tank_name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )


class WeightAndBalanceSeatRowReturn(BaseWeightAndBalanceReportReturn):
    """
    This class defines the seat_rows data returned to the client, 
    as part of the  W&B report.
    """

    seat_row_id: conint(gt=0)
    seat_row_name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )


class WeightAndBalanceBaggageCompartmentReturn(BaseWeightAndBalanceReportReturn):
    """
    This class defines the baggage_compartment data returned to the client, 
    as part of the  W&B report.
    """
    baggage_compartment_id: conint(gt=0)
    baggage_compartment_name: constr(
        min_length=2,
        max_length=50,
        pattern="^[\-a-zA-Z0-9 ]+$"  # pylint: disable=anomalous-backslash-in-string
    )


class WeightAndBalanceReport(BaseModel):
    """
    This class defines the  W&B report data returned to the user.
    """

    warnings: List[constr(
        strip_whitespace=True,
        max_length=255
    )]
    seats: List[WeightAndBalanceSeatRowReturn]
    compartments: List[WeightAndBalanceBaggageCompartmentReturn]
    fuel_on_board: List[WeightAndBalanceFuelTankReturn]
    fuel_burned_pre_takeoff: WeightAndBalanceFuelReturn
    fuel_burned: List[WeightAndBalanceFuelTankReturn]
    zero_fuel_weight: BaseWeightAndBalanceReportReturn
    ramp_weight: BaseWeightAndBalanceReportReturn
    takeoff_weight: BaseWeightAndBalanceReportReturn
    landing_weight: BaseWeightAndBalanceReportReturn
