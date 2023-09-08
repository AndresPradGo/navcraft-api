"""
Router startup module

Module asigns each router to its url path, and links it to the FastAPI app.

Usage: 
- Import the link_routes function, and pass the FastAPI app as a parameter.

"""

from fastapi import FastAPI

from routes.aircraft import router as aircraft
from routes.aircraft_models import router as aircraft_models
from routes.aircraft_performance_data import router as aircraft_performance_data
from routes.aircraft_weight_balance_data import router as aircraft_weight_balnace_data
from routes.auth import router as auth
from routes.flights import router as flights
from routes.manage_vfr_waypoints import router as manage_vfr_waypoints
from routes.users import router as users
from routes.user_waypoints import router as user_waypoints
from routes.vfr_waypoints import router as vfr_waypoints
from routes.runways import router as runways


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
    app.include_router(flights, prefix="/flights")
    app.include_router(aircraft_models, prefix="/aircraft-models")
    app.include_router(aircraft, prefix="/aircraft")
    app.include_router(aircraft_performance_data,
                       prefix="/aircraft-performance-data")
    app.include_router(aircraft_weight_balnace_data,
                       prefix="/aircraft-weight-balance-data")
    app.include_router(vfr_waypoints, prefix="/vfr_waypoints")
    app.include_router(manage_vfr_waypoints, prefix="/manage_vfr_waypoints")
    app.include_router(user_waypoints, prefix="/user_waypoints")
    app.include_router(runways, prefix="/runways")
