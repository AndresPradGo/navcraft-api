"""
FastAPI auth router

This module defines the FastAPI auth router.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
from utils import common_responses
from utils.db import get_db
from utils.hasher import Hasher

router = APIRouter(tags=["Auth"])


@router.post("/", status_code=status.HTTP_200_OK, response_model=schemas.JWTData)
async def login_endpoint(
    login_data: schemas.AuthenticationData,
    db: Session = Depends(get_db)
):
    """
    Authenticate Endpoint.

    Parameters: 
    - login_data (dict): an object with email and password fields.

    Returns: 
    - Dic: dictionary with JWT.

    Raise:
    - HTTPException (401): if login details are invalid.
    - HTTPException (500): if there is a server error. 
    """

    try:
        user = db.query(models.User).filter(
            models.User.email == login_data.email).first()
    except IntegrityError:
        raise common_responses.internal_server_error()

    exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid credentials, please enter a valid email and password."
    )

    if not user:
        raise exception

    if not Hasher.verify(login_data.password, user.password):
        raise exception

    token = user.generate_auth_token()

    return {"access_token": token, "token_type": "bearer"}
