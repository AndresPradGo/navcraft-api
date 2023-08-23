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
    """

    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255
    )
    weight_lb: confloat(ge=0)


class UserReturn(UserBase):
    """
    This class defines the pydantic schema used to return 
    user data to the client.

   Attributes:
    - id (Integer): user id.
    - is_admin (Boolean): true if the user is admin. Admin users have privileges 
      like adding aerodromes and aircraft base models.
    - is_master (Boolean): true if the user is master. Only master users can add 
      new admin users. Master users have to be Admin Users.
    """

    id: int
    is_admin: bool
    is_master: bool


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
        max_length=25
    )

    @validator('password')
    @classmethod
    def check_passwrod_criteria(clc, password: float) -> float:
        '''
        Classmethod to check if password contains at least 1 uppercase, 
        1 lowercase and 1 number characters.

        Parameters:
        - value (string): the password to be validated.

        Returns:
        (string):password after validation is complete.
        '''

        if any(c.isspace() or c == '\n' for c in password):
            raise ValueError(
                "Password cannot contain any white spaces or line breaks.")

        if not any(c.isupper() for c in password):
            raise ValueError(
                "Password must have at least one uppercase character.")

        if not any(c.islower() for c in password):
            raise ValueError(
                "Password must have at least one lowercase character.")

        if not any(c.isdigit() for c in password):
            raise ValueError("Password must have at least one digit.")

        return password

    @validator('weight_lb')
    @classmethod
    def round_user_weight(clc, value: float) -> float:
        '''
        Classmethod to round weight_lb input value to 1 decimal place.

        Parameters:
        - value (float): the weight to be validated.

        Returns:
        (float): weight value rounded to 1 decimal place.

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


class PassengerProfileData(BaseModel):
    """
    This class defines the pydantic schema used to
    send passenger profile data.

   Attributes:
    - name (String): passenger name.
    - weight_lb (Decimal): passenger weight in lbs.
    """

    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255
    )
    weight_lb: confloat(ge=0)


class PassengerProfileReturn(PassengerProfileData):
    """
    This class defines the pydantic schema used to
    return passenger profile data to the client.

   Attributes:
    - id (Integer): passenger id.
    """

    id: int
