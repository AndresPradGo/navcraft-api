"""
Useful Reusable Functions

Usage: 
- Import the required function and call it.
"""

import json
from typing import List, Any

from sqlalchemy.orm import Session

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


async def get_user_id_from_email(email: str, db: Session):
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

    user_id = db.query(models.User.id).filter(
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

    if not len(right_runways) + len(left_runways) + len(center_runways) + len(none_runways) == len(runways) or\
            not len(runways_with_position) + len(none_runways) == len(all_runways):
        return False

    return True


def get_table_header(table_name: str):
    """
    Gets the table headers for csv downloadable files.

    Parameters:
    - table_name (str): name of the table.

    Returns: 
    - dict: dictionary with table headers.
    """
    with open("config/csv_headers.json", "r") as json_file:
        tables = json.load(json_file)

    return tables[table_name]
