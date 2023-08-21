"""
Pydantic user scemas

This module defines the user pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import Optional, Any

from pydantic import BaseModel, constr, EmailStr, conint, confloat, NaiveDatetime, validator, model_validator


class UserEmail(BaseModel):
    """
    This class defines the pydantic user_email schema.

   Attributes:
    - email (String): user email.
    """

    email: EmailStr


class UserBase(UserEmail):
    """
    This class defines the pydantic user_base schema.

   Attributes:
    - name (String): user name.
    - weight_lb (Decimal): user weight in lbs.
    - is_admin (Boolean): true if the user is admin. Admin users have privileges 
      like adding aerodromes and aircraft base models.
    - is_master (Boolean): true if the user is master. Only master users can add 
      new admin users. Master users have to be Admin Users.
    """

    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255
    )
    weight_lb: confloat(ge=0)
    is_admin: Optional[bool] = None
    is_master: Optional[bool] = None


class UserData(UserBase):
    """
    This class defines the pydantic user_data schema.

   Attributes:
    - password (String): user password.
    """

    password: constr(
        strip_whitespace=True,
        strict=True,
        min_length=8,
        max_length=255
    )

    @validator('weight_lb')
    @classmethod
    def round_magnetic_variation(clc, value: float) -> float:
        '''
        Classmethod to round weight_lb input value to 1 decimal place.

        Parameters:
        - value (float): the values to be validated.

        Returns:
        (float) :weight value rounded to 1 decimal place.

        '''
        return round(value, 1)


class JWTData(BaseModel):
    """
    This class defines the pydantic jwt_data schema, 
    to return the JWT after authentication.

    Attributes:
    - jwt (String): the Jason Web Token.
    - type (String): the token type.
    """

    access_token: str
    token_type: str
