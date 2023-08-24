"""
Router startup module

Module asigns each router to its url path, and links it to the FastAPI app.

Usage: 
- Import the link_routes function, and pass the FastAPI app as a parameter.

"""

from fastapi import FastAPI

from routes.auth import router as auth
from routes.users import router as users
from routes.waypoints import router as waypoints


def link_routes(app: FastAPI) -> None:
    """
    This function asigns each router to its url path, 
    and links it to the FastAPI app.

    Parameters:
    - app (FastAPI): The FastAPI app.

    Returns: None
    """

    print("------ LINKING ROUTES ------")
    app.include_router(auth, prefix="/login")
    app.include_router(users, prefix="/users")
    app.include_router(waypoints, prefix="/waypoints")
