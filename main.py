"""
FastAPI Main Flight Planner API

This module is the entry point of the flight-planner API. 
It creates the FastAPI app and runs the startup package.

Usage: 
- Run this module to start the FastAPI development server.

"""

from fastapi import FastAPI

from startup.create_db import create_database
from startup.db_setup import set_charracter_set, create_tables
from startup.routes import link_routes

app = FastAPI()

create_database()
set_charracter_set()
create_tables()
link_routes(app)
