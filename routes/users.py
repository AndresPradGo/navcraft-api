"""
FastAPI users router

This module defines the FastAPI users router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from utils.functions import get_user_id_from_email


router = APIRouter(tags=["Users"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[schemas.UserReturnBasic])
async def get_all_users(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_master_user)
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
    return db.query(models.User).filter(or_(
        not_(id),
        models.User.id == id
    )).order_by(models.User.id).all()


@router.get("/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturn)
async def get_user_profile_data(
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
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
    user = db.query(models.User).filter(
        models.User.email == current_user.email).first()

    return user


@router.get(
    "/passenger-profiles",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.PassengerProfileReturn]
)
async def get_passenger_profiles(
    id: Optional[int] = 0,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Passenger Profiles Endpoint.

    Parameters:
    id (int): optional profile id.

    Returns: 
    - list: list of dictionaries with the profiles.

    Raise:
    - HTTPException (401): validation fails.
    - HTTPException (500): if there is a server error. 
    """
    profiles = db.query(models.PassengerProfile).filter(and_(
        models.User.email == current_user.email,
        or_(
            not_(id),
            models.PassengerProfile.id == id
        )
    )).order_by(models.PassengerProfile.name).all()

    return profiles


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserReturnBasic)
async def sign_in(
    user: schemas.UserSigin,
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

    email_exists = db.query(models.User.id).filter(
        models.User.email == user.email).first()

    if email_exists:
        msg = f"Email {user.email} is already registered, please choose another email or login to your existing account."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    hashed_pswd = auth.Hasher.bcrypt(user.password)

    new_user = models.User(
        email=user.email,
        name=user.name,
        password=hashed_pswd,
        is_admin=False,
        is_master=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    response.headers["x-access-token"] = new_user.generate_auth_token()
    response.headers["x-token-type"] = "bearer"
    return new_user


@router.post(
    "/new-passenger-profile",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PassengerProfileReturn
)
async def add_new_passenger_profile(
    passenger_profile_data: schemas.PassengerProfileData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Endpoint to add a new passenger profile

    Parameters: 
    - passenger_profile_data (dict): dictionary with passenger profile data.

    Returns: 
    - Dic: dictionary with passenger profile data and database id.

    Raise:
    - HTTPException (400): if user already has a passenger profile with the given name.
    - HTTPException (401): not able to validate user.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    passenger_already_exists = db.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.name == passenger_profile_data.name,
        models.PassengerProfile.creator_id == user_id
    )).first()
    if passenger_already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Passenger with name {passenger_profile_data.name} already exists."
        )

    new_passenger_profile = models.PassengerProfile(
        name=passenger_profile_data.name,
        weight_lb=passenger_profile_data.weight_lb,
        creator_id=user_id
    )
    db.add(new_passenger_profile)
    db.commit()
    db.refresh(new_passenger_profile)

    return new_passenger_profile


@router.put("/email/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturnBasic)
async def change_email(
    user_data: schemas.UserEmail,
    response: Response,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Change User Email Endpoint.

    Parameters: 
    - user_data (dict): schema with the new user email.

    Returns: 
    - Dic: dictionary with the user data.

    Raise:
    - HTTPException (400): if user with new email already exists.
    - HTTPException (401): if user is invalid or trying to update other user's data.
    - HTTPException (500): if there is a server error. 
    """

    # Check if email is equal to current email
    if user_data.email == current_user.email:
        new_user = db.query(models.User).filter(
            models.User.email == user_data.email).first()
        response.headers["x-access-token"] = new_user.generate_auth_token()
        response.headers["x-token-type"] = "bearer"
        return new_user

    # Check if user with new email already exists
    user_with_email = db.query(models.User).filter(
        models.User.email == user_data.email).first()
    if user_with_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {user_data.email}, already exists."
        )

    # Update User email
    user = db.query(models.User).filter(
        models.User.email == current_user.email)
    if not user.first():
        raise common_responses.internal_server_error()
    user.update({"email": user_data.email})
    db.commit()

    # Return new user data
    new_user = db.query(models.User).filter(
        models.User.email == user_data.email).first()
    response.headers["x-access-token"] = new_user.generate_auth_token()
    response.headers["x-token-type"] = "bearer"
    return new_user


@router.put("/password/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturnBasic)
async def change_password(
    user_data: schemas.PasswordChangeData,
    response: Response,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Change Password Endpoint.

    Parameters: 
    - user_data (dict): dictionary current password and new password.

    Returns: 
    - Dic: dictionary with the user data.

    Raise:
    - HTTPException (400): if new password is not in the right format.
    - HTTPException (401): if user is invalid or trying to update other user's data.
    - HTTPException (500): if there is a server error. 
    """
    # Get user from db
    user_query = db.query(models.User).filter(
        models.User.email == current_user.email)
    if not user_query.first():
        raise common_responses.internal_server_error()

    # Check current_password provided
    if not auth.Hasher.verify(user_data.current_password, user_query.first().password):
        raise common_responses.invalid_credentials()

    # Updata password to new password
    user_data.password = auth.Hasher.bcrypt(user_data.password)
    user_query.update({"password": user_data.password})
    db.commit()

    # Return User data
    new_user = db.query(models.User).filter(
        models.User.email == current_user.email).first()
    response.headers["x-access-token"] = new_user.generate_auth_token()
    response.headers["x-token-type"] = "bearer"
    return new_user


@router.put("/me", status_code=status.HTTP_200_OK, response_model=schemas.UserEditProfileData)
async def edit_user_profile(
    user_data: schemas.UserEditProfileData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit User Endpoint.

    Parameters: 
    - user (dict): dictionary with the user data.

    Returns: 
    - Dic: dictionary with the user data.

    Raise:
     - HTTPException (400): if user with new email already exists.
    - HTTPException (401): if user is invalid or trying to update other user's data.
    - HTTPException (500): if there is a server error. 
    """
    # Get User from db
    user = db.query(models.User).filter(
        models.User.email == current_user.email)
    if not user.first():
        raise common_responses.invalid_credentials()
    # Update User
    user.update(user_data.model_dump())
    db.commit()
    # Return User Data
    new_user = db.query(models.User).filter(
        models.User.email == current_user.email).first()

    return new_user


@router.put(
    "/admin-user/{id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.UserReturnBasic
)
async def grant_revoke_admin_privileges_or_deactivate(
    id: int,
    make_admin: bool,
    activate: bool,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_master_user)
):
    """
    Grant or Revoke Admin Privileges Endpoint. Only master users can use this endpoint.

    Parameters: 
    - user (dict): dictionary with user id and admin set to true or false.

    Returns: 
    - Dic: dictionary with user data.

    Raise:
    - HTTPException (400): if the user being updated is a master user.
    - HTTPException (401): if user making the change is not master user.
    - HTTPException (404): user not found.
    - HTTPException (500): if there is a server error. 
    """

    user = db.query(models.User).filter(models.User.id == id)

    if not user.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The user you're trying to update, is not in the database."
        )
    if user.first().is_master:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The user you're trying to update, is a master user."
        )

    user.update({"is_admin": make_admin, "is_active": activate})
    db.commit()
    new_user = user.first()
    db.refresh(new_user)

    return new_user


@router.put(
    "/passenger-profile/{id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.PassengerProfileReturn
)
async def edit_existing_passenger_profile(
    id: int,
    passenger_profile_data: schemas.PassengerProfileData,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit a Passenger Profile

    Parameters: 
    - id (int): passenger profile id
    - passenger_profile_data (dict): dictionary with passenger profile data.

    Returns: 
    - Dic: dictionary with passenger profile data and database id.

    Raise:
    - HTTPException (400): if user already has a passenger profile with the given name.
    - HTTPException (401): not able to validate user.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db=db)

    passenger_already_exists = db.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.name == passenger_profile_data.name,
        models.PassengerProfile.creator_id == user_id,
        not_(models.PassengerProfile.id == id)
    )).first()
    if passenger_already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Passenger with name {passenger_profile_data.name} already exists. Please select another name."
        )

    passenger_profile = db.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.id == id,
        models.PassengerProfile.creator_id == user_id,
    ))
    if not passenger_profile.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The passenger profile you're trying to update, is not in the database."
        )

    passenger_profile.update(passenger_profile_data.model_dump())
    db.commit()
    new_passenger_profile = db.query(models.PassengerProfile).filter(
        models.PassengerProfile.id == id).first()

    return new_passenger_profile


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Account.

    Parameters: None

    Returns: None

    Raise:
    - HTTPException (404): user not found.
    - HTTPException (401): if user making the change is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    deleted = db.query(models.User).\
        filter(models.User.email == current_user.email).\
        delete(synchronize_session=False)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Your account has already been deleted."
        )
    db.commit()


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    id: int,
    db: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_master_user)
):
    """
    Delete user endpoint, for master users to delete othe accounts.

    Parameters: 
    id (int): user id.

    Returns: None

    Raise:
    - HTTPException (401): if user making the change is not master user.
    - HTTPException (404): user not found.
    - HTTPException (500): if there is a server error. 
    """

    deleted = db.query(models.User).filter(models.User.id == id).\
        delete(synchronize_session=False)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The user you're trying to delete, is not in the database."
        )
    db.commit()


@router.delete("/passenger-profile/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_passenger_profile(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete passenger profile.

    Parameters: 
    id (int): passenger profile id.

    Returns: None

    Raise:
    - HTTPException (401): invalid credentials.
    - HTTPException (404): passenger profile not found.
    - HTTPException (500): if there is a server error. 
    """

    user_id = await get_user_id_from_email(email=current_user.email, db=db)
    deleted = db.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.id == id,
        models.PassengerProfile.creator_id == user_id
    )).delete(synchronize_session=False)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The passenger profile you're trying to delete, is not in the database."
        )
    db.commit()
