"""
FastAPI Main Flight Planner API

This module is the entry point of the flight-planner API. 
It creates the FastAPI app and runs the startup package.

Usage: 
- Run this module to start the FastAPI development server.

"""

from fastapi import FastAPI

from startup.db import create_tables
from startup.routes import link_routes

app = FastAPI()

create_tables()
link_routes(app)
