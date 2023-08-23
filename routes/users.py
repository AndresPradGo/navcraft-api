"""
FastAPI users router

This module defines the FastAPI users router.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db


router = APIRouter(tags=["Users"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[schemas.UserReturn])
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


@router.get("/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturn)
async def get_user_profile_data(
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_user)
):
    """
    Get Profile Data Endpoint.

    Parameters: None

    Returns: 
    - dict: dictionary with user data.

    Raise:
    - HTTPException (401): validation fails.
    - HTTPException (500): if there is a server error. 
    """

    try:
        user = db.query(models.User).filter(
            models.User.email == current_user["email"]).first()
    except IntegrityError:
        raise common_responses.internal_server_error()

    return user


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserReturn)
async def sign_in(
    user: schemas.UserData,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Post User Endpoint.

    Parameters: 
    - user (dict): the user object to be added.

    Returns: 
    - Dic: dictionary with the user data.

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

    response.headers["x-access-token"] = new_user.generate_auth_token()
    response.headers["x-token-type"] = "bearer"
    return new_user


@router.put("/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturn)
async def update_user_profile(
    user_data: schemas.UserData,
    response: Response,
    db: Session = Depends(get_db),
    current_user: schemas.UserEmail = Depends(auth.validate_user)
):
    """
    Update User Endpoint.

    Parameters: 
    - user (dict): dictionary with the user data.

    Returns: 
    - Dic: dictionary with the user data.

    Raise:
     - HTTPException (400): if user with new email already exists.
    - HTTPException (401): if user is invalid or trying to update other user's data.
    - HTTPException (500): if there is a server error. 
    """

    try:
        user_with_email = db.query(models.User).filter(
            models.User.email == user_data.email).first()

        if user_with_email and not user_data.email == current_user["email"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {user_data.email}, already exists."
            )
    except IntegrityError as e:
        raise common_responses.internal_server_error()

    try:
        user = db.query(models.User).filter(
            models.User.email == current_user["email"])

        if not user.first():
            raise common_responses.invalid_credentials()

        user_data.password = auth.Hasher.bcrypt(user_data.password)
        user.update(user_data.model_dump())
        db.commit()
        new_user = db.query(models.User).filter(
            models.User.email == user_data.email).first()
    except IntegrityError:
        raise common_responses.internal_server_error()

    response.headers["x-access-token"] = new_user.generate_auth_token()
    response.headers["x-token-type"] = "bearer"
    return new_user


@router.put("/make-admin/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.UserReturn)
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

    return new_user
