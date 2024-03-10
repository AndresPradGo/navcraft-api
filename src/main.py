"""
FastAPI Main Flight Planner API

This module is the entry point of the flight-planner API. 
It creates the FastAPI app and runs the startup package.

Usage: 
- Run this module to start the FastAPI development server.

"""

from fastapi import FastAPI

from startup.add_documentation import add_documentation
from startup.create_db import create_database
from startup.config_cors import config_cors
from startup import error_logger
from startup.migrate_db import migrate_db
from startup.routes import link_routes
from startup.schedule_clean_db_job import schedule_clean_db_job


error_logger.init_logger()

app = FastAPI(
    docs_url=None, redoc_url=None,
    title="NavCraft API",
    version="1.0.0",
    swagger_favicon_url="../public/logo.png",
    description="Helping pilots craft the perfect navigation flight plans. NavCraft API uses aircraft performance data, and Canadian aviation rules, regulations and definitions, to produce VFR flight plans that include: \n \n - navigation logs, \n \n - weight and balance graphs and calculations, \n \n - fuel calculations, \n \n - takeoff and landing distances."
)

add_documentation(app)
create_database()
migrate_db()
config_cors(app)
link_routes(app)
schedule_clean_db_job()
