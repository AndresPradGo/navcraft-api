"""
Pydantic user schemas

This module defines the user pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from typing import List

from pydantic import BaseModel, constr, EmailStr, conint, confloat, field_validator

from utils.functions import clean_string


class PassengerProfileData(BaseModel):
    """
    This class defines the pdata-structure used to send passenger profile data.
    """

    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9 ]+$",
    )
    weight_lb: confloat(ge=0)


class PassengerProfileReturn(PassengerProfileData):
    """
    This class defines the data-structure used to
    return passenger profile data to the client.
    """

    id: conint(gt=0)


class UserEmail(BaseModel):
    """
    This class defines the user email data structure.
    """

    email: EmailStr


class UserName(BaseModel):
    """
    This class defines the user name data structure.
    """

    name: constr(
        strip_whitespace=True,
        strict=True,
        min_length=2,
        max_length=255,
        pattern="^[-a-zA-Z0-9 ]+$",
    )

    @field_validator('name')
    @classmethod
    def clean_user_name(cls, value: str) -> str:
        '''
        Classmethod to clean name string.

        Parameters:
        - value (str): the name string to be validated.

        Returns:
        (str): cleaned name string.

        '''
        return clean_string(value)


class UserReturnBasic(UserName, UserEmail):
    """
    This class defines the data-structure used to return 
    user-profile data to the client.
    """

    id: conint(gt=0)
    is_admin: bool
    is_master: bool
    is_active: bool
    weight_lb: confloat(ge=0)


class UserReturn(UserReturnBasic):
    """
    This class defines the data-structure used to return 
    user data to the client, including the list of passenger profies.
    """

    passenger_profiles: List[PassengerProfileReturn]


class UserPassword(BaseModel):
    """
    This class defines the user password data structure.
    """

    password: constr(
        strip_whitespace=True,
        strict=True,
        min_length=8,
        max_length=25
    )

    @field_validator('password')
    @classmethod
    def check_passwrod_criteria(cls, password: float) -> float:
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


class UserWeight(BaseModel):
    """
    This class defines the user weight data structure.
    """
    weight_lb: confloat(ge=0)

    @field_validator('weight_lb')
    @classmethod
    def round_user_weight(cls, value: float) -> float:
        '''
        Classmethod to round weight_lb input value to 1 decimal place.

        Parameters:
        - value (float): the weight to be validated.

        Returns:
        (float): weight value rounded to 1 decimal place.

        '''
        return round(value, 1)


class UserSigin(UserPassword, UserName, UserEmail):
    '''
    This class defines the data required to sign in as a new user.
    '''


class UserEditProfileData(UserName, UserWeight):
    '''
    This class defines the data required for editing profile data.
    '''


class PasswordChangeData(UserPassword):
    '''
    This class defines the data required for user password change.
    '''
    current_password: constr(
        strip_whitespace=True,
        strict=True,
        min_length=8,
        max_length=25
    )


class JWTData(BaseModel):
    '''
    This class defines the JWT Return
    '''
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    This class defines the JWT Payload.
    """
    email: str | None = None
    is_admin: bool
    is_master: bool
    is_active: bool
