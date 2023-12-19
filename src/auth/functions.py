"""
Authentication and Authorization Functions

This module creates authentication and authorization functions.

Usage: 
- All functions are imported in the __init__.py file, so the functions 
  can be called directly form the auth package.

"""
from typing import Annotated, List

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from utils import common_responses, environ_variable_tools as environ
import schemas


def get_jwt_payload(token: str):
    """
    This function decodes a JWT and returns the payload data. 

    Parameters:
    - token (str): Jason Web Token.


    Returns: 
    - dict: jwt payload data.

     Raise:
    - HTTPException (401): if user is not valid.
    """

    try:
        payload = jwt.decode(
            token,
            environ.get("jwt_secret_key"),
            algorithms=environ.get("jwt_algorithm")
        )
    except JWTError:
        # pylint: disable=raise-missing-from
        raise common_responses.invalid_credentials()

    return payload


def validate_user(
    token: Annotated[
        str,
        Depends(OAuth2PasswordBearer(tokenUrl="login"))
    ]
):
    """
    This function validates user and returns the user email. 

    Parameters:
    - token (str): Jason Web Token.

    Returns: 
    - dict: {"email": user email}.

     Raise:
    - HTTPException (401): if user is not valid.
    """

    jwt_payload = get_jwt_payload(token)
    user_email: str = jwt_payload.get("email")
    active: bool = jwt_payload.get("active")
    permissions: List[str] = jwt_payload.get("permissions")

    if user_email is None or permissions is None:
        raise common_responses.invalid_credentials()

    token_data = schemas.TokenData(
        email=user_email,
        is_admin="admin" in permissions,
        is_master="master" in permissions,
        is_active=active
    )

    return token_data


def validate_admin_user(
    token: Annotated[
        str,
        Depends(OAuth2PasswordBearer(tokenUrl="login"))
    ]
):
    """
    This function validates an admin user and returns the user email. 

    Parameters:
    - token (str): Jason Web Token.

    Returns: 
    - dict: {"email": user email}.

     Raise:
    - HTTPException (401): if user is not valid, or user is not admin.
    """

    token_data = validate_user(token)

    if not token_data.is_admin or not token_data.is_active:
        raise common_responses.invalid_credentials()

    return token_data


def validate_master_user(
    token: Annotated[
        str,
        Depends(OAuth2PasswordBearer(tokenUrl="login"))
    ]
):
    """
    This function validates a master user and returns the user email. 

    Parameters:
    - token (str): Jason Web Token.

    Returns: 
    - dict: {"email": user email}.

     Raise:
    - HTTPException (401): if user is not valid, or user is not admin,
      or user is not master.
    """

    token_data = validate_admin_user(token)

    if not token_data.is_master:
        raise common_responses.invalid_credentials()

    return token_data
