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
    added_enroute_time_hours = Column(
        DECIMAL(4, 2),
        nullable=False,
        default=0.0
    )
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

    briefing_radius_nm = Column(Integer, nullable=False, default=5)
    diversion_radius_nm = Column(Integer, nullable=False, default=10)

    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="SET NULL",
            onupdate="CASCADE"
        )
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
    persons_on_board = Relationship(
        "PersonOnBoard",
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
    fuel_tanks = Relationship(
        "Fuel",
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
    temperature_c = Column(Integer, nullable=False, default=15)
    wind_direction = Column(Integer)
    wind_magnitude_knot = Column(Integer, nullable=False, default=0)
    altimeter_inhg = Column(DECIMAL(4, 2), nullable=False, default=29.92)
    temperature_last_updated = Column(DateTime)
    wind_last_updated = Column(DateTime)
    altimeter_last_updated = Column(DateTime)
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

    official_weather = Relationship(
        "AerodromeWeatherReport",
        back_populates="departure",
        passive_deletes=True,
        passive_updates=True,
        uselist=False
    )


class Arrival(DepartureAndArrival):
    """
    This class defines the database arrivals table.
    """

    __tablename__ = "arrivals"

    flight = Relationship("Flight", back_populates="arrival")
    aerodrome = Relationship("Aerodrome", back_populates="arrivals")

    official_weather = Relationship(
        "AerodromeWeatherReport",
        back_populates="arrival",
        passive_deletes=True,
        passive_updates=True,
        uselist=False
    )


class Leg(BaseModel):
    """
    This class defines the database legs table.
    """

    __tablename__ = "legs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(Integer, nullable=False)
    altitude_ft = Column(Integer, nullable=False, default=2000)
    temperature_c = Column(Integer, nullable=False, default=13)
    wind_direction = Column(Integer)
    wind_magnitude_knot = Column(Integer, nullable=False, default=0)
    altimeter_inhg = Column(DECIMAL(4, 2), nullable=False, default=29.92)
    temperature_last_updated = Column(DateTime)
    wind_last_updated = Column(DateTime)
    altimeter_last_updated = Column(DateTime)
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
    official_weather = Relationship(
        "EnrouteWeatherReport",
        back_populates="leg",
        passive_deletes=True,
        passive_updates=True,
        uselist=False
    )


class PersonOnBoard(BaseModel):
    """
    This class defines the database persons_on_board table.
    """

    __tablename__ = "persons_on_board"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seat_number = Column(Integer, nullable=False)
    name = Column(String(255))
    weight_lb = Column(DECIMAL(5, 2))
    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )
    seat_row_id = Column(
        Integer,
        ForeignKey(
            "seat_rows.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )
    passenger_profile_id = Column(
        Integer,
        ForeignKey(
            "passenger_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )

    flight = Relationship("Flight", back_populates="persons_on_board")
    seat_row = Relationship("SeatRow", back_populates="persons_on_board")
    user = Relationship("User", back_populates="persons_on_board")
    passenger_profile = Relationship(
        "PassengerProfile", back_populates="persons_on_board")


class Baggage(BaseModel):
    """
    This class defines the database baggages table.
    """

    __tablename__ = "baggages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    weight_lb = Column(DECIMAL(5, 2), nullable=False, default=5.0)
    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    baggage_compartment_id = Column(
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


class Fuel(BaseModel):
    """
    This class defines the database fuel table.
    """

    __tablename__ = "fuel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gallons = Column(DECIMAL(5, 2), nullable=False, default=0.0)

    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    fuel_tank_id = Column(
        Integer,
        ForeignKey(
            "fuel_tanks.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    flight = Relationship("Flight", back_populates="fuel_tanks")
    fuel_tank = Relationship(
        "FuelTank",
        back_populates="flights"
    )
