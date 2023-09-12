"""
Sqlalchemy flight model

This module defines the flight, leg, and related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from datetime import datetime


from sqlalchemy import Column, Integer, DECIMAL, DateTime, String, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class Flight(BaseModel):
    """
    This class defines the database flights table.
    """

    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    departure_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow()
    )
    bhp_percent = Column(Integer, nullable=False, default=65)
    reserve_fuel_hours = Column(
        DECIMAL(4, 2),
        nullable=False,
        default=0.5
    )
    contingency_fuel_hours = Column(
        DECIMAL(4, 2),
        nullable=False,
        default=0.0
    )
    fuel_on_board_gallons = Column(
        DECIMAL(5, 2),
        nullable=False,
        default=0.0
    )
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="SET NULL",
            onupdate="CASCADE"
        )
    )
    status_id = Column(
        Integer,
        ForeignKey(
            "flight_status.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    pilot_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aircraft = Relationship("Aircraft", back_populates="flights")
    status = Relationship("FlightStatus", back_populates="flights")
    departure = Relationship(
        "Departure",
        back_populates="flight",
        passive_deletes=True,
        passive_updates=True,
        uselist=False
    )
    arrival = Relationship(
        "Arrival",
        back_populates="flight",
        passive_deletes=True,
        passive_updates=True,
        uselist=False
    )
    legs = Relationship(
        "Leg",
        back_populates="flight",
        passive_deletes=True,
        passive_updates=True
    )
    passengers = Relationship(
        "Passenger",
        back_populates="flight",
        passive_deletes=True,
        passive_updates=True
    )
    baggages = Relationship(
        "Baggage",
        back_populates="flight",
        passive_deletes=True,
        passive_updates=True
    )
    pilot = Relationship("User", back_populates="flights")


class DepartureAndArrival(BaseModel):
    """
    This class defines the database departures and arrivals base model, 
    which will be the parent for the Departures and Arrivals models.
    """

    __abstract__ = True

    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True,
        nullable=False,
        unique=True
    )
    wind_direction = Column(Integer, nullable=False, default=0)
    wind_magnitude_knot = Column(Integer, nullable=False, default=0)
    temperature_c = Column(Integer, nullable=False, default=15)
    altimeter_inhg = Column(DECIMAL(4, 2), nullable=False, default=29.92)
    weather_valid_from = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow(),
        onupdate=datetime.utcnow()
    )
    weather_valid_to = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow(),
        onupdate=datetime.utcnow()
    )
    aerodrome_id = Column(
        Integer,
        ForeignKey(
            "aerodromes.id",
            ondelete="SET NULL",
            onupdate="CASCADE"
        )
    )


class Departure(DepartureAndArrival):
    """
    This class defines the database departures table.
    """

    __tablename__ = "departures"

    flight = Relationship("Flight", back_populates="departure")
    aerodrome = Relationship("Aerodrome", back_populates="departures")


class Arrival(DepartureAndArrival):
    """
    This class defines the database arrivals table.
    """

    __tablename__ = "arrivals"

    flight = Relationship("Flight", back_populates="arrival")
    aerodrome = Relationship("Aerodrome", back_populates="arrivals")


class Leg(BaseModel):
    """
    This class defines the database legs table.
    """

    __tablename__ = "legs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(Integer, nullable=False)
    altitude_ft = Column(Integer, nullable=False, default=1000)
    temperature_c = Column(Integer, nullable=False, default=13)
    wind_direction = Column(Integer)
    wind_magnitude_knot = Column(Integer, nullable=False, default=0)
    weather_valid_from = Column(DateTime)
    weather_valid_to = Column(DateTime)
    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    flight = Relationship("Flight", back_populates="legs")
    flight_waypoint = Relationship(
        "FlightWaypoint",
        back_populates="leg",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )


class FlightStatus(BaseModel):
    """
    This class defines the database flight_status table.
    """

    __tablename__ = "flight_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(50), nullable=False, unique=True)

    flights = Relationship(
        "Flight",
        back_populates="status",
        passive_deletes=True,
        passive_updates=True
    )


class Passenger(BaseModel):
    """
    This class defines the database passengers table.
    """

    __tablename__ = "passengers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(4, 2))
    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )
    seat_id = Column(
        Integer,
        ForeignKey(
            "seat_rows.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    flight = Relationship("Flight", back_populates="passengers")
    seat_row = Relationship("SeatRow", back_populates="passengers")


class Baggage(BaseModel):
    """
    This class defines the database baggages table.
    """

    __tablename__ = "baggages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(4, 2), nullable=False, default=5.0)
    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    compartment_id = Column(
        Integer,
        ForeignKey(
            "baggage_compartments.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    flight = Relationship("Flight", back_populates="baggages")
    baggage_compartment = Relationship(
        "BaggageCompartment",
        back_populates="baggages"
    )
