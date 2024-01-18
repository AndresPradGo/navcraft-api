"""
FastAPI users router

This module defines the FastAPI users router endpoints.

Usage: 
- Import the router to add it to the FastAPI app.

"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, Response
import pytz
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session

import auth
import models
import schemas
from utils import common_responses
from utils.db import get_db
from functions.data_processing import get_user_id_from_email


router = APIRouter(tags=["Users"])


@router.get("", status_code=status.HTTP_200_OK, response_model=List[schemas.UserReturnBasic])
def get_all_users(
    limit: Optional[int] = -1,
    start: Optional[int] = 0,
    user_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_master_user)
):
    """
    Get All Users Endpoint.

    Parameters: 
    - limit (int): number of results.
    - start (int): index of the first user.
    - user_id (int): user id.


    Returns: 
    - list[dict[UserReturnBasic]]: list of user dictionaries.

    Raise:
    - HTTPException (401): if user is not master user.
    - HTTPException (500): if there is a server error. 
    """

    users = db_session.query(models.User).filter(or_(
        not_(user_id),
        models.User.id == user_id
    )).order_by(models.User.id).all()

    limit = len(users) if limit == -1 else limit

    return [
        {
            **user.__dict__,
            "created_at": pytz.timezone('UTC').localize((user.created_at)),
            "last_updated": pytz.timezone('UTC').localize((user.last_updated)),
        } for user in users[start:start + limit]
    ]


@router.get("/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturn)
def get_user_profile_data(
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Profile Data Endpoint.

    Parameters: None

    Returns: 
    - dict[UserReturn]: dictionary with user data.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    user = db_session.query(models.User).filter(
        models.User.email == current_user.email).first()

    if user is None:
        raise common_responses.invalid_credentials()

    profiles = db_session.query(models.PassengerProfile).filter(
        models.PassengerProfile.creator_id == user.id
    ).order_by(models.PassengerProfile.name).all()

    return {
        **user.__dict__,
        "passenger_profiles": profiles,
        "created_at": pytz.timezone('UTC').localize((user.created_at)),
        "last_updated": pytz.timezone('UTC').localize((user.last_updated)),
    }


@router.get(
    "/passenger-profiles",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.PassengerProfileReturn]
)
def get_passenger_profiles(
    profile_id: Optional[int] = 0,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Get Passenger Profiles Endpoint.

    Parameters:
    profile_id (int): optional profile id.

    Returns: 
    - list[dict[PassengerProfileReturn]]: list of dictionaries with the profiles.

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    profiles = db_session.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.creator_id == user_id,
        or_(
            not_(profile_id),
            models.PassengerProfile.id == profile_id
        )
    )).order_by(models.PassengerProfile.name).all()

    return profiles


@router.post("", status_code=status.HTTP_201_CREATED, response_model=schemas.JWTData)
def register(
    user: schemas.UserRegister,
    db_session: Session = Depends(get_db)
):
    """
    Post User Endpoint.

    Parameters: 
    - user (dict[UserRegister]): the user data to be added.

    Returns: 
    - dic[JWTData]: dictionary with the JWT user data.

    Raise:
    - HTTPException (400): if user already exists.
    - HTTPException (500): if there is a server error. 
    """

    email_exists = db_session.query(models.User.id).filter(
        models.User.email == user.email).first()

    if email_exists:
        msg = f"Email {user.email} is already registered."
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
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    return {"access_token": new_user.generate_auth_token(), "token_type": "Bearer"}


@router.post("/trial", status_code=status.HTTP_201_CREATED, response_model=schemas.JWTData)
def register_trial(db_session: Session = Depends(get_db)):
    """
    Post Trial Endpoint.

    Parameters: None

    Returns: 
    - dic[JWTData]: dictionary with the JWT user data.

    Raise:
    - HTTPException (500): if there is a server error. 
    """

    # Create a unique email
    email_exists = True
    while email_exists:
        date_time = datetime.utcnow().strftime("%y%m%d%H%M%S%f")[:-4]
        email = f"user{date_time}@trial.com"

        email_in_db = db_session.query(models.User.id).filter(
            models.User.email == email).first()

        email_exists = email_in_db is not None

    hashed_pswd = auth.Hasher.bcrypt(f"Pass8725{date_time}")

    new_user = models.User(
        email=email,
        name="Trial User",
        password=hashed_pswd,
        is_admin=False,
        is_master=False,
        is_trial=True
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    return {"access_token": new_user.generate_auth_token(), "token_type": "Bearer"}


@router.post(
    "/passenger-profile",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PassengerProfileReturn
)
def add_new_passenger_profile(
    passenger_profile_data: schemas.PassengerProfileData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Endpoint to add a new passenger profile

    Parameters: 
    - passenger_profile_data (dict[PassengerProfileData]): dictionary with 
      passenger profile data.

    Returns: 
    - dic[PassengerProfileReturn]: dictionary with passenger profile 
      data and database id.

    Raise:
    - HTTPException (400): if user already has a passenger profile with the given name.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)

    passenger_already_exists = db_session.query(models.PassengerProfile).filter(and_(
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
    db_session.add(new_passenger_profile)
    db_session.commit()
    db_session.refresh(new_passenger_profile)

    return new_passenger_profile


@router.put("/email/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturnBasic)
def change_email(
    user_data: schemas.UserEmail,
    response: Response,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Change User Email Endpoint.

    Parameters: 
    - user_data (dict[UserEmail]): dict with the new user email.

    Returns: 
    - dic[UserReturnBasic]: dictionary with the user data.

    Raise:
    - HTTPException (400): if user with new email already exists.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    # Check if email is equal to current email
    if user_data.email == current_user.email:
        new_user = db_session.query(models.User).filter(
            models.User.email == user_data.email).first()
        response.headers["x-access-token"] = new_user.generate_auth_token()
        response.headers["x-token-type"] = "Bearer"
        return new_user

    # Check if user with new email already exists
    user_with_email = db_session.query(models.User).filter(
        models.User.email == user_data.email).first()
    if user_with_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {user_data.email}, already exists."
        )

    # Update User email
    user = db_session.query(models.User).filter(
        models.User.email == current_user.email)
    if not user.first():
        raise common_responses.internal_server_error()
    user.update({"email": user_data.email})
    db_session.commit()

    # Return new user data
    new_user = db_session.query(models.User).filter(
        models.User.email == user_data.email).first()
    response.headers["x-access-token"] = new_user.generate_auth_token()
    response.headers["x-token-type"] = "Bearer"
    return {
        **new_user.__dict__,
        "created_at": pytz.timezone('UTC').localize((new_user.created_at)),
        "last_updated": pytz.timezone('UTC').localize((new_user.last_updated)),
    }


@router.put("/password/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturnBasic)
def change_password(
    user_data: schemas.PasswordChangeData,
    response: Response,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Change Password Endpoint.

    Parameters: 
    - user_data (dict[PasswordChangeData]): dictionary current 
      password and new password.

    Returns: 
    - dic[UserReturnBasic]: dictionary with the user data.

    Raise:
    - HTTPException (400): if new password is not in the right format.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Get user from database
    user_query = db_session.query(models.User).filter(
        models.User.email == current_user.email)
    if not user_query.first():
        raise common_responses.internal_server_error()

    # Check current_password provided
    if not auth.Hasher.verify(user_data.current_password, user_query.first().password):
        raise common_responses.invalid_credentials()

    # Updata password to new password
    user_data.password = auth.Hasher.bcrypt(user_data.password)
    user_query.update({"password": user_data.password})
    db_session.commit()

    # Return User data
    new_user = db_session.query(models.User).filter(
        models.User.email == current_user.email).first()
    response.headers["x-access-token"] = new_user.generate_auth_token()
    response.headers["x-token-type"] = "Bearer"
    return {
        **new_user.__dict__,
        "created_at": pytz.timezone('UTC').localize((new_user.created_at)),
        "last_updated": pytz.timezone('UTC').localize((new_user.last_updated)),
    }


@router.put("/me", status_code=status.HTTP_200_OK, response_model=schemas.UserReturnBasic)
def edit_user_profile(
    user_data: schemas.UserEditProfileData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit User Endpoint.

    Parameters: 
    - user (dict[UserEditProfileData]): dictionary with the user data.

    Returns: 
    - dic[UserReturnBasic]: dictionary with the user data.

    Raise:
     - HTTPException (400): if user with new email already exists.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """
    # Get User from database
    user = db_session.query(models.User).filter(
        models.User.email == current_user.email)
    if not user.first():
        raise common_responses.invalid_credentials()
    # Update User
    user.update(user_data.model_dump())
    db_session.commit()
    # Return User Data
    new_user = db_session.query(models.User).filter(
        models.User.email == current_user.email).first()

    return {
        **new_user.__dict__,
        "created_at": pytz.timezone('UTC').localize((new_user.created_at)),
        "last_updated": pytz.timezone('UTC').localize((new_user.last_updated)),
    }


@router.put(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.UserReturnBasic
)
def grant_revoke_admin_privileges_or_deactivate(
    user_id: int,
    data: schemas.EditUserData,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_master_user)
):
    """
    Grant or Revoke Admin Privileges Endpoint. Only master users can use this endpoint.

    Parameters: 
    - user_id (int): user id.
    - data (dict[EditUserData]): (make_admin(bool), activate (bool))

    Returns: 
    - dic[UserReturnBasic]: dictionary with user data.

    Raise:
    - HTTPException (400): if the user being updated is a master user.
    - HTTPException (401): if user making the change is not master user.
    - HTTPException (404): user not found.
    - HTTPException (500): if there is a server error. 
    """

    user = db_session.query(models.User).filter(models.User.id == user_id)

    if not user.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user you're trying to update, is not in the database."
        )
    if user.first().is_master:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user you're trying to update, is a master user."
        )

    user.update({"is_admin": data.make_admin, "is_active": data.activate})
    db_session.commit()
    new_user = user.first()
    db_session.refresh(new_user)

    return {
        **new_user.__dict__,
        "created_at": pytz.timezone('UTC').localize((new_user.created_at)),
        "last_updated": pytz.timezone('UTC').localize((new_user.last_updated)),
    }


@router.put(
    "/passenger-profile/{profile_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.PassengerProfileReturn
)
def edit_existing_passenger_profile(
    profile_id: int,
    passenger_profile_data: schemas.PassengerProfileData,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Edit a Passenger Profile

    Parameters: 
    - profile_id (int): passenger profile id
    - passenger_profile_data (dict[PassengerProfileData]): 
      dictionary with passenger profile data.

    Returns: 
    - dict[PassengerProfileReturn]: dictionary with passenger profile 
      data and database id.

    Raise:
    - HTTPException (400): if user already has a passenger profile with the given name.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)

    passenger_already_exists = db_session.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.name == passenger_profile_data.name,
        models.PassengerProfile.creator_id == user_id,
        not_(models.PassengerProfile.id == profile_id)
    )).first()
    if passenger_already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Passenger with name {passenger_profile_data.name} already exists."
        )

    passenger_profile = db_session.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.id == profile_id,
        models.PassengerProfile.creator_id == user_id,
    ))
    if not passenger_profile.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The passenger profile you're trying to update, is not in the database."
        )

    passenger_profile.update(passenger_profile_data.model_dump())
    db_session.commit()
    new_passenger_profile = db_session.query(models.PassengerProfile).filter(
        models.PassengerProfile.id == profile_id).first()

    return new_passenger_profile


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete Account.

    Parameters: None

    Returns: None

    Raise:
    - HTTPException (404): user not found.
    - HTTPException (401): if user is not authenticated.
    - HTTPException (500): if there is a server error. 
    """

    deleted = db_session.query(models.User).\
        filter(models.User.email == current_user.email).\
        delete(synchronize_session=False)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your account has already been deleted."
        )
    db_session.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db_session: Session = Depends(get_db),
    _: schemas.TokenData = Depends(auth.validate_master_user)
):
    """
    Delete user endpoint, for master users to delete othe accounts.

    Parameters: 
    user_id (int): user id.

    Returns: None

    Raise:
    - HTTPException (401): if user making the change is not master user.
    - HTTPException (404): user not found.
    - HTTPException (500): if there is a server error. 
    """

    deleted = db_session.query(models.User).filter(models.User.id == user_id).\
        delete(synchronize_session=False)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user you're trying to delete, is not in the database."
        )
    db_session.commit()


@router.delete("/passenger-profile/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_passenger_profile(
    profile_id: int,
    db_session: Session = Depends(get_db),
    current_user: schemas.TokenData = Depends(auth.validate_user)
):
    """
    Delete passenger profile.

    Parameters: 
    profile_id (int): passenger profile id.

    Returns: None

    Raise:
    - HTTPException (401): if user is not authenticated.
    - HTTPException (404): passenger profile not found.
    - HTTPException (500): if there is a server error. 
    """

    user_id = get_user_id_from_email(
        email=current_user.email, db_session=db_session)
    deleted = db_session.query(models.PassengerProfile).filter(and_(
        models.PassengerProfile.id == profile_id,
        models.PassengerProfile.creator_id == user_id
    )).delete(synchronize_session=False)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The passenger profile you're trying to delete, is not in the database."
        )
    db_session.commit()
