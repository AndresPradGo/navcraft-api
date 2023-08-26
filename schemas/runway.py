"""
Pydantic waypoint scemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional

from pydantic import BaseModel, constr, conint, confloat, validator

from utils.functions import clean_string


class RunwaySurfaceData(BaseModel):
    """
    This class defines the pydantic runway_surface_data schema, for data input to endpoints.

   Attributes:
    - surface (String): runway surface.
      1 being the best performing surface.
    """

    surface: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern='^[-a-zA-Z ]+$',
    )

    @validator('surface')
    @classmethod
    def clean_surface_string(clc, value: str) -> str:
        '''
        Classmethod to clean surface string.

        Parameters:
        - value (str): the surface string t to be validated.

        Returns:
        (str): cleaned surface string.

        '''
        return clean_string(value)


class RunwaySurfaceReturn(RunwaySurfaceData):
    """
    This class defines the pydantic runway_surface_return schema, for data return from endpoints.

   Attributes:
    - id (Integer): runway surface id.
    """

    id: conint(gt=0)
