"""
Waypoint query functions

This module holds reusable waypoint and aerodrome query functions.

Usage: 
- Import the required functions.

"""

from sqlalchemy.orm import Session

import models
import schemas
from utils import common_responses


async def manage_vfr_waypoints(waypoints: schemas.WaypointDataList, db: Session, creator_id: int):
    """
    This function receives a list of vfr waypoints, and uses it 
    to update the vfr_waypoints table in the database.

    Parameters: 
    - waypoints (WaypointDataList pydantic schema): list of waypoint data.
    - db (sqlalchemy Session): database session.
    - creator_id (int): id of the user.

    Returns: 
    sqlalchemy Session: db session with the actions to be commited.

    Raise:
    - HTTPException (400): if the list includes aerodrome codes, 
      or some of the codes are repeated.
    """

    waypoinst_in_db = db.query(models.VfrWaypoint).filter(
        models.VfrWaypoint.code.in_([w.code for w in waypoints]))

    there_are_aerodromes = db.query(models.Aerodrome).filter(models)
