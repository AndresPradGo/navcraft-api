"""
FastAPI auth router

This module defines the FastAPI auth router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext  # pylint: disable=unused-import
from sqlalchemy.orm import Session

import models
import schemas
from utils import common_responses
from utils.db import get_db
from auth import Hasher

router = APIRouter(tags=["Auth"])


@router.post("", status_code=status.HTTP_200_OK, response_model=schemas.JWTData)
def login(
    login_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: Session = Depends(get_db)
):
    """
    Authentication Endpoint
    """

    user = db_session.query(models.User).filter(
        models.User.email == login_data.username).first()

    if not user:
        raise common_responses.invalid_credentials()

    if not Hasher.verify(login_data.password, user.password):
        raise common_responses.invalid_credentials()

    token = user.generate_auth_token()

    return {"access_token": token, "token_type": "Bearer"}
