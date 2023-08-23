"""
User query functions

This module holds reusable user query functions.

Usage: 
- Import the required functions.

"""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from utils import common_responses


async def get_id_from(email: str, db: Session):
    """
    This method queries the db for the user with the provided email, 
    and returns the user id.

    Parameters:
    - email (str): the user email.
    - db: an sqlalchemy db Session to query the database.

    Returns: 
    - int: the user id.

    Raises:
    - HTTPException (401): if it doesn't find a user with the provided email.
    - HTTPException (500): if there is a server error. 
    """

    try:
        user_id = db.query(models.User.id).filter(
            models.User.email == email).first()
        if not user_id:
            raise common_responses.invalid_credentials()
    except IntegrityError:
        raise common_responses.internal_server_error()

    return user_id[0]
