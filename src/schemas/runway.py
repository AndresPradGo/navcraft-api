"""
Pydantic waypoint schemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional

from pydantic import BaseModel, constr, conint, field_validator, model_validator, AwareDatetime

from functions.data_processing import clean_string


class RunwayDataEdit(BaseModel):
    """
    This class defines the data-structure required from client to update runway data.
    """

    length_ft: int
    landing_length_ft: Optional[int] = None
    intersection_departure_length_ft: Optional[int] = None
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

    @model_validator(mode='after')
    @classmethod
    def validate_runway_lengths(cls, values):
        """
        This function checks that landing length and intersection departure 
        length are less than or equal to total length. If landing lenth is 
        not provided, it will be equal to total length.
        """

        if values.landing_length_ft is None:
            values.landing_length_ft = values.length_ft
        elif values.landing_length_ft > values.length_ft:
            raise ValueError(
                "Landing length cannot be longer than total runway length.")

        if values.intersection_departure_length_ft is not None:
            if values.intersection_departure_length_ft > values.length_ft:
                raise ValueError(
                    "Intersection departure length cannot be longer than total runway length.")

        return values


class RunwayData(RunwayDataEdit):
    """
    This class defines the data-structure rquired form the client to post new runways.
    """

    aerodrome_id: int


class RunwayReturn(RunwayData):
    """
    This class defines the data-structure used to return runway data to the client.
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
    created_at_utc: AwareDatetime
    last_updated_utc: AwareDatetime


class RunwaySurfaceData(BaseModel):
    """
    This class defines the data-structure required from the client to post a new runway-surface.
    """

    surface: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern="^[-a-zA-Z ']+$",
    )

    @field_validator('surface')
    @classmethod
    def clean_surface_string(cls, value: str) -> str:
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
    This class defines the data-structure used to return runway-surface data to the client.
    """

    id: conint(gt=0)