"""
Pydantic waypoint scemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional

from pydantic import BaseModel, constr, conint, validator

from utils.functions import clean_string


class RunwayDataEdit(BaseModel):
    """
    This class defines the pydantic runway_data schema, for data input to put endpoints.

   Attributes:
   - length (int): runway surface id.
   - number (int): runway number.
   - position (str): runway position could be right, left, center or None.
   - surface_id (int): runway surface id.
    """

    length_ft: int
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
    surface_id: int


class RunwayData(RunwayDataEdit):
    """
    This class defines the pydantic runway_data schema, for data input to post endpoints.

   Attributes:
    - aerodrome_id (int): runway surface id.

    """

    aerodrome_id: int


class RunwayReturn(RunwayData):
    """
    This class defines the pydantic runway_return schema, for data return from endpoints.

   Attributes:
    - id (Integer): runway id.
    - surface (String): runway surface.
    - aerodrome (String): aerodrome code.
    """

    id: conint(gt=0)
    surface: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern="^[-a-zA-Z ']+$",
    )
    aerodrome: constr(
        strip_whitespace=True,
        to_upper=True,
        min_length=2,
        max_length=50,
        pattern='^[-a-zA-Z0-9]+$',
    )


class RunwaySurfaceData(BaseModel):
    """
    This class defines the pydantic runway_surface_data schema, for data input to endpoints.

   Attributes:
    - surface (String): runway surface.
    """

    surface: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern="^[-a-zA-Z ']+$",
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
