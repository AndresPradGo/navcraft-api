"""
Useful Reusable Functions

Usage: 
- Import the required function and call it.
"""

from typing import List, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, Query

import models
from utils import common_responses


def clean_string(input_string: str) -> str:
    '''
    This functions takes a string and clens it by:
    - Removing leading and trailing white spaces.
    - Converts to lowercase and capitalizes first letter.
    - Replaces consecutive white spaces with a single space.

    Parameters:
    - input_string (str): string to be cleaned.

    Returns:
    str: cleaned string.
    '''

    return ' '.join([word.capitalize() for word in input_string.strip().split()])


async def get_user_id_from_email(email: str, db_session: Session):
    """
    This method queries the db for the user with the provided email, 
    and returns the user id.

    Parameters:
    - email (str): the user email.
    - db_session: an sqlalchemy db Session to query the database.

    Returns: 
    - int: the user id.

    Raises:
    - HTTPException (401): if it doesn't find a user with the provided email.
    - HTTPException (500): if there is a server error. 
    """
    user_id = db_session.query(models.User.id).filter(
        models.User.email == email).first()
    if not user_id:
        raise common_responses.invalid_credentials()

    return user_id[0]


def runways_are_unique(runways: List[Any]):
    """
    Checks if a list of runways is unique

    Parameters:
    - runways (list): a list of RunwayData instances

    Returns: 
    - bool: true is list is unique, and false otherwise
    """

    right_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position == "R"}
    left_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position == "L"}
    center_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position == "C"}
    none_runways = {
        f"{r.aerodrome_id}{r.number}" for r in runways if r.position is None}

    runways_with_position = right_runways | left_runways | center_runways
    all_runways = runways_with_position | none_runways

    runway_position_repeated = not len(right_runways) + len(left_runways)\
        + len(center_runways) + len(none_runways) == len(runways)

    runway_number_without_position_repeated = not len(runways_with_position)\
        + len(none_runways) == len(all_runways)

    if runway_position_repeated or\
            runway_number_without_position_repeated:
        return False

    return True


def check_performance_profile_and_permissions(
        db_session: Session,
        user_id: int,
        user_is_active_admin: bool,
        profile_id: int,
        auth_non_admin_get_model: bool = False
) -> Query[models.PerformanceProfile]:
    """
    Checks if user has permission to edit an aircraft performance profile.

    Parameters:
    - db_session (sqlalchemy Session): database session.
    - user_id (int): user id.
    - user_is_active_admin (bool): true if user is an active admin.
    - profile_id (int): performance profile id.

    Returns: 
    - Query[models.PerformanceProfile]: returns the performance profile query.
    """

    performance_profile_query = db_session.query(
        models.PerformanceProfile).filter_by(id=profile_id)
    if performance_profile_query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Performance profile with ID {profile_id} not found."
        )

    performance_for_model = performance_profile_query.first().aircraft_id is None

    if performance_for_model:
        if not user_is_active_admin and not auth_non_admin_get_model:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to edit this performance profile"
            )
    else:
        aircraft = db_session.query(models.Aircraft).filter_by(
            id=performance_profile_query.first().aircraft_id).first()

        if not aircraft.owner_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to edit this performance profile"
            )

    return performance_profile_query
