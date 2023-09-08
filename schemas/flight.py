"""
Pydantic flight schemas

This module defines the flight related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from pydantic import BaseModel


class FlightStatusReturn(BaseModel):
    """
    This class defines the flight-status data returned to the client.
    """
    id: int
    status: str
