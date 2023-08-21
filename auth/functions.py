"""
Authentication and Authorization Functions

This module creates authentication and authorization functions.

Usage: 
- All functions are imported in the __init__.py file, so the functions 
  can be called directly form the auth package.

"""

from typing import Annotated, List

from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel

from utils import environ_variable as environ


_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials, please log in with a valid email and password.",
    headers={"WWW-Authenticate": "Bearer"},
)


class TokenData(BaseModel):
    """
    This class defines the pydantic token_data schema.

   Attributes:
    - email (String): user email.
    - is_admin (Boolean): true if user is admin.
    - is_master (Boolean): true if user is master.
    """
    email: str | None = None
    is_admin: bool
    is_master: bool


def get_jwt_payload(token: str):
    """
    This function decodes a JWT and returns the payload data. 

    Parameters:
    - token (str): Jason Web Token.


    Returns: 
    - TokenData: pydantic token_data schema.

     Raise:
    - HTTPException (401): if user is not valid.
    """

    try:
        payload = jwt.decode(
            token,
            environ.get("jwtSecretKey"),
            algorithms=environ.get("jwtAlgorithm")
        )
        user_email: str = payload.get("email")
        permissions: List[str] = payload.get("permissions")

        if user_email is None or permissions is None:
            raise _CREDENTIALS_EXCEPTION

        token_data = TokenData(
            email=user_email,
            is_admin="admin" in permissions,
            is_master="master" in permissions
        )

    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    return token_data


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

    if not jwt_payload.is_admin:
        raise

    return {"email": jwt_payload.email}


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

    jwt_payload = get_jwt_payload(token)

    if not jwt_payload.is_admin:
        raise _CREDENTIALS_EXCEPTION

    return {"email": jwt_payload.email}


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

    jwt_payload = get_jwt_payload(token)

    if not jwt_payload.is_admin or not jwt_payload.is_master:
        raise _CREDENTIALS_EXCEPTION

    return {"email": jwt_payload.email}
