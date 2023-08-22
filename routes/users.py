"""
FastAPI users router

This module defines the FastAPI users router.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
from utils import common_responses
import auth
from utils.db import get_db


router = APIRouter(tags=["Users"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[schemas.UserReturnForMasterUsers])
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_master_user)
):
    """
    Get All Users Endpoint.

    Parameters: None

    Returns: 
    - list: list of user dictionaries.

    Raise:
    - HTTPException (401): if user is not master user.
    - HTTPException (500): if there is a server error. 
    """

    try:
        users = db.query(models.User).all()
    except IntegrityError:
        raise common_responses.internal_server_error()

    return users


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserBase)
async def sign_in(
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

    hashed_pswd = auth.Hasher.bcrypt(user.password)

    try:
        new_user = models.User(
            email=user.email,
            name=user.name,
            weight_lb=user.weight_lb,
            password=hashed_pswd,
            is_admin=False,
            is_master=False,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        raise common_responses.internal_server_error()

    return new_user


@router.put("/make-admin/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.UserReturnForMasterUsers)
async def grant_revoke_admin_privileges(
    id,
    make_admin: bool,
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_master_user)
):
    """
    Grant or Revoke Admin Privileges Endpoint. Only master users can use this endpoint.

    Parameters: 
    - user (dict): dictionary with user id and admin set to true or false.

    Returns: 
    - Dic: dictionary user id and is_admin.

    Raise:
    - HTTPException (400): if user to be updated is not in database.
    - HTTPException (401): if user making the change is not master user.
    - HTTPException (500): if there is a server error. 
    """
    print(type(id))
    try:
        user = db.query(models.User).filter(models.User.id == id)

        if not user.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User id {id} is not valid."
            )

        user.update({"is_admin": make_admin})
        db.commit()
        new_user = user.first()
        db.refresh(new_user)
    except IntegrityError:
        raise common_responses.internal_server_error()

    return (new_user)
