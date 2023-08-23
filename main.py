"""
FastAPI Main Flight Planner API

This module is the entry point of the flight-planner API. 
It creates the FastAPI app and runs the startup package.

Usage: 
- Run this module to start the FastAPI development server.

"""

from fastapi import FastAPI
import asyncio

from startup.create_db import create_database
from startup.db_setup import set_charracter_set, create_tables
from startup.routes import link_routes
from startup.populate_db import populate_db

app = FastAPI()

create_database()
set_charracter_set()
create_tables()
populate_db()
link_routes(app)
