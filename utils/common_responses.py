"""
Common Server Responses

This module defines common and general server responses.

Usage: 
- Import the function returning the response you want to use, and call it.

"""

import re

from fastapi import status, HTTPException


def internal_server_error():
    """
    This function returns an internal server error HTTPException.

    Parameters: None

    Returns: 
    HTTPException: internal server error response.
    """
    message = '''
        An unexpected server error occurred. Our team has been 
        notified and is investigating the issue. We apologize 
        for any inconvenience.
    '''

    response = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=re.sub(r'\s+', ' ', message).strip()
    )

    return response


def invalid_credentials():
    """
    This function returns an invalid credantials HTTPException.

    Parameters: None

    Returns: 
    HTTPException: invalid credantials response.
    """
    response = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials, please log in with a valid email and password.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return response
