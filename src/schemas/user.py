"""
Pydantic user schemas

This module defines the user pydantic schemas for data validation.

Usage: 
- Import the required schema to validate data at the API endpoints.

"""

from typing import List

from pydantic import BaseModel, constr, EmailStr, conint, confloat, field_validator, AwareDatetime

from functions.data_processing import clean_string


class PassengerProfileData(BaseModel):
    """
    Schema that outlines the data required to create a new passenger profile
    """

    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[A-Za-z0-9 /.'-]+$",
    )
    weight_lb: confloat(allow_inf_nan=False, ge=0, le=999.94)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str) -> str:
        """
        Classmethod to clean name string.

        Parameters:
        - value (str): the name string to be validated.

        Returns:
        (str): cleaned name string.

        """
        return clean_string(value)

    @field_validator('weight_lb')
    @classmethod
    def round_user_weight(cls, value: float) -> float:
        """
        Classmethod to round weight_lb input value to 1 decimal place.

        Parameters:
        - value (float): the weight to be validated.

        Returns:
        (float): weight value rounded to 2 decimal place.

        """
        return round(value, 2)


class PassengerProfileReturn(PassengerProfileData):
    """
    Schema that outlines the passenger profile data to return to the client
    """

    id: conint(gt=0)


class UserEmail(BaseModel):
    """
    Schema that outlines the email data to register, update and return a user
    """

    email: EmailStr


class UserName(BaseModel):
    """
    Schema that outlines the name data to register, update and return a user
    """

    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[A-Za-z0-9 /.'-]+$",
    )

    @field_validator('name')
    @classmethod
    def clean_user_name(cls, value: str) -> str:
        """
        Classmethod to clean name string.

        Parameters:
        - value (str): the name string to be validated.

        Returns:
        (str): cleaned name string.

        """
        return clean_string(value)


class UserReturnBasic(UserName, UserEmail):
    """
    Schema that outlines the most basic user data to return to the client
    """

    id: conint(gt=0)
    is_admin: bool
    is_master: bool
    is_active: bool
    is_trial: bool
    created_at: AwareDatetime
    last_updated: AwareDatetime
    weight_lb: confloat(ge=0, le=999.94)


class UserReturn(UserReturnBasic):
    """
    Schema that outlines the complete user data to return to the client
    """
    passenger_profiles: List[PassengerProfileReturn]


class UserPassword(BaseModel):
    """
    Schema that outlines defines the user password data structure
    """
    password: constr(
        strip_whitespace=True,
        strict=True,
        min_length=8,
        max_length=25
    )

    @field_validator('password')
    @classmethod
    def check_passwrod_criteria(cls, password: str) -> str:
        """
        Classmethod to check if password contains at least 1 uppercase, 
        1 lowercase and 1 number characters.

        Parameters:
        - value (string): the password to be validated.

        Returns:
        (string):password after validation is complete.
        """

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


class UserWeight(BaseModel):
    """
    Schema that outlines the user weight data
    """
    weight_lb: confloat(ge=0, le=999.94)

    @field_validator('weight_lb')
    @classmethod
    def round_user_weight(cls, value: float) -> float:
        """
        Classmethod to round weight_lb input value to 1 decimal place.

        Parameters:
        - value (float): the weight to be validated.

        Returns:
        (float): weight value rounded to 2 decimal place.

        """
        return round(value, 2)


class UserRegister(UserPassword, UserName, UserEmail):
    """
    Schema that outlines the data required to register a new user
    """


class UserEditProfileData(UserName, UserWeight):
    """
    Schema that outlines the data required to edit a user profile
    """


class PasswordChangeData(UserPassword):
    """
    Schema that outlines the data required to change a user's password
    """
    current_password: constr(
        strip_whitespace=True,
        strict=True,
        min_length=8,
        max_length=25
    )


class JWTData(BaseModel):
    """
    Schema that outlines the JWT data to return to the client, as an authentication result
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Schema that outlines the JWT payload
    """
    email: str | None = None
    is_admin: bool
    is_master: bool
    is_active: bool


class EditUserData(BaseModel):
    """
    Schema that outlines the data required for a master user to update another user
    """
    make_admin: bool
    activate: bool
