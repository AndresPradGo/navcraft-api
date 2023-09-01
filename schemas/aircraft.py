"""
Pydantic aircraft schemas

This module defines the aircraft related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional

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
        pattern="^[\.\-a-zA-Z0-9\(\) ]+$"
    )

    @field_validator('name')
    @classmethod
    def clean_name(clc, value: str) -> str:
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
    def round_density(clc, value: float) -> float:
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
    def clean_name(clc, value: str) -> str:
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
        to_upper=True,
        min_length=2,
        max_length=255,
        pattern="^[\-a-zA-Z0-9 ]+$"
    )

    @field_validator('performance_profile_name')
    @classmethod
    def clean_performance_profile_name(clc, value: str) -> str:
        '''
        Classmethod to clean performance_profile_name string.

        Parameters:
        - value (str): the performance_profile_name string to be validated.

        Returns:
        (str): cleaned performance_profile_name string.
        '''
        return clean_string(value)


class PerformanceProfilePostReturn(PerformanceProfilePostData):
    """
    This class defines the data-structure required to return performance profile data
    to the client.
    """

    id: conint(gt=0)


class AircraftModelOfficialPostData(PerformanceProfilePostData):
    '''
    This class defines the data structure reuired from the client, in order to add
    a new official aircraft model to the database as an admin user.
    '''

    make_id: conint(gt=0)
    model: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=255,
        pattern="^[\.\-a-zA-Z0-9\(\) ]+$"
    )
    code: constr(
        to_upper=True,
        strip_whitespace=True,
        min_length=2,
        max_length=5,
        pattern="^[\-a-zA-Z0-9]+$"
    )


class AircraftModelOfficialPostReturn(AircraftModelOfficialPostData):
    """
    This class defines the data-structure required to return Official aircraft model data
    to the client.
    """

    id: conint(gt=0)
    performance_profile_id: conint(gt=0)
