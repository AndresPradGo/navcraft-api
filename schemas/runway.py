"""
Pydantic waypoint scemas

This module defines the waipoint, aerodrome, and related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional

from pydantic import BaseModel, constr, conint, confloat, validator, model_validator


class RunwaySurfaceData(BaseModel):
    """
    This class defines the pydantic runway_surface_data schema, for data input to endpoints.

   Attributes:
    - surface (String): runway surface.
    - performance_level (Integer): integer that organices the surfaces by better performing, 
      1 being the best performing surface.
    """

    surface: constr(
        strip_whitespace=True,
        min_length=2,
        max_length=50,
        pattern='^[-a-zA-Z]+$',
    )
    performance_level: Optional[conint(gt=0)] = None


class RunwaySurfaceReturn(RunwaySurfaceData):
    """
    This class defines the pydantic runway_surface_return schema, for data return from endpoints.

   Attributes:
    - id (Integer): runway surface id.
    """

    id: conint(gt=0)
