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


class WeightAndBalanceFuelReturn(BaseModel):
    """
    This class defines the data structure to return fuel 
    weight and balance data to the client.
    """

    gallons: confloat(allow_inf_nan=False, ge=0, le=999.99)
    density_lb_gal: confloat(gt=0, allow_inf_nan=False, le=99.99)
    fuel_burned_gallons: confloat(allow_inf_nan=False, ge=0, le=999.99)
    take_off_taxi_fuel_gallons: confloat(allow_inf_nan=False, ge=0, le=99.99)

    @model_validator(mode='after')
    @classmethod
    def round_values(cls, values):
        '''
        Classmethod to check to round float values.

        Parameters:
        - values (Any): The object with float values.

        Returns:
        (Any) : The object of rounded values.
        '''
        values.gallons = round(values.gallons, 2)
        values.density_lb_gal = round(values.density_lb_gal, 2)
        values.fuel_burned_gallons = round(values.fuel_burned_gallons, 2)
        values.take_off_taxi_fuel_gallons = round(
            values.take_off_taxi_fuel_gallons, 2)

        return values


class FlightWeightAndBalanceReturn(BaseModel):
    """
    This class defines the flight W&B data returned to the user.
    """

    warnings: List[constr(
        strip_whitespace=True,
        max_length=255,
        pattern='^[.,--a-zA-Z0-9 ]+$',
    )]
    persons_on_board: List[PersonOnBoardReturn]
    baggages: List[FlightBaggageReturn]
    fuel_on_board: WeightAndBalanceFuelReturn
