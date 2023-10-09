""" 
CORS Configuration

This module configures the CORS to accept requests from the client.

Usage: 
- Import the config_cors function into the main.py module and call it. 

"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils import environ_variable_tools as environ


def config_cors(app: FastAPI):
    """
    This function configures the CORS to allow requests form the client.

    Parameters:
    - app (FastAPI): The FastAPI app.

    Returns: None
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[environ.get('client_origin'),],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
