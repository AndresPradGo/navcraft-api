"""
FastAPI users router

This module defines the FastAPI users router.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
from utils import common_responses
from utils.hasher import Hasher
from utils.db import get_db


router = APIRouter(tags=["Users"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserBase)
async def sign_in_endpoint(
    user: schemas.UserData,
    db: Session = Depends(get_db)
):
    """
    Post User Endpoint.

    Parameters: 
    - user (dict): the user object to be added.

    Returns: 
    - Dic: dictionary with the user data and JWT.

    Raise:
    - HTTPException (400): if user already exists.
    - HTTPException (500): if there is a server error. 
    """

    try:
        email_exists = db.query(models.User.id).filter(
            models.User.email == user.email).first()
    except IntegrityError:
        raise common_responses.internal_server_error()

    if email_exists:
        msg = f"Email {user.email} is already registered, please choose another email or login to your existing account."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    # hash password

    hashed_pswd = Hasher.bcrypt(user.password)

    try:
        new_user = models.User(
            email=user.email,
            name=user.name,
            weight_lb=user.weight_lb,
            password=hashed_pswd,
            is_admin=user.is_admin,
            is_master=user.is_master,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        raise common_responses.internal_server_error()

    return new_user
