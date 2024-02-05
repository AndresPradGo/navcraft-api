"""
Router startup module

Module asigns each router to its url path, and links it to the FastAPI app.

Usage: 
- Import the link_routes function, and pass the FastAPI app as a parameter.

"""

from fastapi import FastAPI

# pylint: disable=no-name-in-module
from routes.aircraft.aircraft import router as aircraft
from routes.aircraft.aircraft_models import router as aircraft_models
from routes.aircraft.aircraft_performance_data import router as aircraft_performance_data
from routes.aircraft.aircraft_weight_balance_data import router as aircraft_weight_balnace_data
from routes.aircraft.aircraft_arrangement_data import router as aircraft_arrangement_data
from routes.auth import router as auth
from routes.flights.flights import router as flights
from routes.flights.flight_legs import router as flight_legs
from routes.flights.flight_plans import router as flight_plans
from routes.flights.flight_weight_balance_data import router as flight_weight_balance_data
from routes.users import router as users
from routes.waypoints.manage_waypoints import router as manage_waypoints
from routes.waypoints.waypoints import router as waypoints
from routes.waypoints.admin_waypoints import router as admin_waypoints
from routes.waypoints.runways import router as runways


def link_routes(app: FastAPI) -> None:
    """
    This function asigns each router to its url path, 
    and links it to the FastAPI app.
    """

    print("------ LINKING ROUTES ------")
    app.include_router(auth, prefix="/api/login")
    app.include_router(users, prefix="/api/users")
    app.include_router(
        flight_plans,
        prefix="/api/flight-plans"
    )
    app.include_router(flights, prefix="/api/flights")
    app.include_router(flight_legs, prefix="/api/flight-legs")
    app.include_router(
        flight_weight_balance_data,
        prefix="/api/flight-weight-balance-data"
    )
    app.include_router(aircraft_models, prefix="/api/aircraft-models")
    app.include_router(aircraft, prefix="/api/aircraft")
    app.include_router(
        aircraft_performance_data,
        prefix="/api/aircraft-performance-data"
    )
    app.include_router(
        aircraft_weight_balnace_data,
        prefix="/api/aircraft-weight-balance-data"
    )
    app.include_router(
        aircraft_arrangement_data,
        prefix="/api/aircraft-arrangement-data"
    )
    app.include_router(waypoints, prefix="/api/waypoints")
    app.include_router(admin_waypoints, prefix="/api/admin-waypoints")
    app.include_router(manage_waypoints, prefix="/api/manage-waypoints")
    app.include_router(runways, prefix="/api/runways")
