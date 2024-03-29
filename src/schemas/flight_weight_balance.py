"""
Pydantic flight weight and balance schemas

This module defines the flight weight and balance related pydantic schemas for data validation.

Usage: 
- Import the required schema to validate data at the API endpoints.

"""

from typing import Optional

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
    Schema that outlines the data required to add a new person to a flight
    """

    seat_row_id: conint(gt=0)
    seat_number: conint(gt=0)
    name: Optional[constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9' ]+$",
    )] = None
    weight_lb: Optional[confloat(allow_inf_nan=False, ge=0, le=999.94)] = None
    is_me: Optional[bool] = None
    passenger_profile_id: Optional[conint(gt=0)] = None

    @model_validator(mode='after')
    @classmethod
    def validate_data_source(cls, values):
        """
        Classmethod to check that only 1 out of 3 possible data sources is provided.
        """

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
    Schema that outlines the person-on-board data to return to the client
    """
    id: conint(gt=0)
    seat_row_id: conint(gt=0)
    seat_number: conint(gt=0)
    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9' ]+$",
    )
    weight_lb: confloat(allow_inf_nan=False, ge=0, le=999.94)
    user_id: Optional[conint(gt=0)] = None
    passenger_profile_id: Optional[conint(gt=0)] = None


class FlightBaggageData(BaseModel):
    """"
    Schema that outlines the data required to add luggage to a flight
    """

    baggage_compartment_id: conint(gt=0)
    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9' ]+$",
    )
    weight_lb: confloat(allow_inf_nan=False, ge=0, le=999.94)

    @model_validator(mode='after')
    @classmethod
    def round_weight_and_clean_name(cls, values):
        """
        Classmethod to round the weight and clean name string.

        Parameters:
        - values (Any): input values.

        Returns:
        (Any): input values with rounded weight and clean name.
        """
        values.weight_lb = round(values.weight_lb, 2)
        values.name = clean_string(values.name)

        return values


class FlightBaggageReturn(FlightBaggageData):
    """"
    Schema that outlines the luggage data to return to the client
    """
    id: conint(gt=0)


class FlightFuelReturn(BaseModel):
    """"
    Schema that outlines the fuel data to return to the client
    """
    id: conint(gt=0)
    fuel_tank_id: conint(gt=0)
    gallons: confloat(allow_inf_nan=False, ge=0, le=999.94)
    weight_lb: float


class FuelData(BaseModel):
    """"
    Schema that outlines the data required to add fuel to a flight
    """

    gallons: conint(gt=0)
