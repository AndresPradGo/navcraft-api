"""
Pydantic flight schemas

This module defines the flight related pydantic schemas for data validation.

Usage: 
- Import the required schema class to validate data at the API endpoints.

"""

from pydantic import BaseModel, conint, AwareDatetime


class NewFlightData(BaseModel):
    """
    This class defines the flight data requiered to post a new flight.
    """
    departure_time: AwareDatetime
    aircraft_id: conint(gt=0)
    departure_aerodrome_id: conint(gt=0)
    arrival_aerodrome_id: conint(gt=0)


class NewFlightReturn(NewFlightData):
    """
    This class defines the flight data returned to the client after posting a new flight.
    """
    id: conint(gt=0)


class FlightStatusReturn(BaseModel):
    """
    This class defines the flight-status data returned to the client.
    """
    id: int
    status: str
