"""
Sqlalchemy flight model

This module defines the flight, leg, and related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from datetime import datetime

from sqlalchemy import Column, Integer, DECIMAL, DateTime, Float, String, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class Flight(BaseModel):
    """
    This class defines the database flight model.

    Attributes:
    - id (Integer Column): table primary key.
    - departure_time (DateTime Column): estimated departure time.
    - bhp_percent (Integer Column) = percentage of the engine's break hose power used during cruise.
    - reserve_fuel_hours (Decimal Column) = number of hours of reserve fuel.
    - contingency_fuel_hours (Decimal Column) = number of hours of contingency fuel.
    - take_off_fuel_gallons (Decimal Column) = fuel gallons used during start, taxi, runup and takeoff.
    - aircraft_id (Integer Column): foreign key that points to the aircraft table.
    - status_id (Integer Column): foreign key that points to the flight_status table.
    - aircraft (Relationship): Defines the many-to-one relationship with the aircraft table.
    - status (Relationship): Defines the many-to-one relationship with the flight_status table.
    - departure (Relationship): Defines the one-to-one relationship with the departures table.
    - arrival (Relationship): Defines the one-to-one relationship with the arrivals table.
    - legs (Relationship): defines the one-to-many relationship with the legs table.
    - passengers (Relationship): defines the one-to-many relationship with the passengers table.
    - baggages (Relationship): defines the one-to-many relationship with the baggages table.
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
        DECIMAL(precision=3, scale=1),
        nullable=False,
        default=0.5
    )
    contingency_fuel_hours = Column(
        DECIMAL(precision=3, scale=1),
        nullable=False,
        default=0.0
    )
    take_off_fuel_gallons = Column(
        DECIMAL(precision=3, scale=1),
        nullable=False,
        default=1.0
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


class DepartureAndArrival(BaseModel):
    """
    This class defines the databasedepartures and arrivals base model, 
    which will be the parent for the Departures and Arrivals models.

    Attributes:
    - flight_id (Integer Column): table primary key. Also the 
      foreignkey that points to the flights table.
    - wind_direction (Integer Column): wind direction in degrees true.
    - wind_magnitude_knot (Integer Column): wind magnitude in knots.
    - temperature_c (Integer Column): air temperature at aerodrome, in celsius.
    - altimeter_inhg (Decimal Column): altimeter setting at aerodrome, in inHg
    - weather_valid_from (DateTime Column): start-time of validity of weather forecast.
    - weather_valid_to (DateTime Column): end-time of validity of weather forecast.
    - runway_id (Integer Column): foreignkey pointing to the ranway of departure/arrival.
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
    runway_id = Column(
        Integer,
        ForeignKey(
            "runways.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        )
    )


class Departure(DepartureAndArrival):
    """
    This class defines the database departure model.

    Attributes:
    - flight (Relationship): Defines the one-to-one relationship with the flights table.
    - runway (Relationship): Defines the many-to-one relationship with the runways table.
    """

    __tablename__ = "departures"

    flight = Relationship("Flight", back_populates="departure")
    runway = Relationship("Runway", back_populates="departures")


class Arrival(DepartureAndArrival):
    """
    This class defines the database arrival model.

    Attributes:
    - flight (Relationship): Defines the one-to-one relationship with the flights table.
    - runway (Relationship): Defines the many-to-one relationship with the runways table.
    """

    __tablename__ = "arrivals"

    flight = Relationship("Flight", back_populates="arrival")
    runway = Relationship("Runway", back_populates="arrivals")


class Leg(BaseModel):
    """
    This class defines the database leg model.

    Attributes:
    - id (Integer Column): table primary key.
    - sequence (Integer Column): sequence of this leg in the flight.
    - altitude_ft (Integer Column):  altitude in ft above sea level.
    - temperature_c (Integer Column): air temperature at cruise altitude, in celsius.
    - wind_direction (Integer Column): wind direction in degrees true.
    - wind_magnitude_knot (Integer Column): wind magnitude in knots.
    - magnetic_variation (Decimal Column): magnetic variation for the leg.
    - flight_id (Integer Column): foreign key that points to the flights table.
    - waypoint_id (Integer Column): foreign key that points to the waypoints table.
    - flight (Relationship): Defines the many-to-one relationship with the flight table.
    - waypoint (Relationship): Defines the many-to-one relationship with the waypoint table.
    """

    __tablename__ = "legs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(Integer, nullable=False)
    altitude_ft = Column(Integer, nullable=False, default=0)
    temperature_c = Column(Integer, nullable=False, default=15)
    wind_direction = Column(Integer, nullable=False, default=0)
    wind_magnitude_knot = Column(Integer, nullable=False, default=0)
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
    magnetic_variation = Column(
        DECIMAL(precision=3, scale=1),
        nullable=False,
        default=0.0
    )
    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    waypoint_id = Column(
        Integer,
        ForeignKey(
            "waypoints.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )

    flight = Relationship("Flight", back_populates="legs")
    waypoint = Relationship("Waypoint", back_populates="legs")


class FlightStatus(BaseModel):
    """
    This class defines the database flight_status model.

    Attributes:
    - id (Integer Column): table primary key.
    - status (String Column): the flight status (e.g. saved, printed, completed)
    - flights (Relationship): list of flights with the status.
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
    This class defines the database passenger model.

    Attributes:
    - flight_id (Integer Column): foreign key that points to the flights table.
      Also a composite key.
    - profile_id (Integer Column): foreign key that points to the profiles table.
      Also a composite key.
    - seat_id (Integer Column): foreign key that points to the seat_rows table.
    - flight (Relationship): Defines the many-to-one relationship with the flights table.
    - profile (Relationship): Defines the many-to-one relationship with the passenger_profiles table.
    - seat_row (Relationship): Defines the many-to-one relationship with the seat_rows table.
    """

    __tablename__ = "passengers"

    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True
    )
    profile_id = Column(
        Integer,
        ForeignKey(
            "passenger_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True
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
    profile = Relationship("PassengerProfile", back_populates="passengers")
    seat_row = Relationship("SeatRow", back_populates="passengers")


class Baggage(BaseModel):
    """
    This class defines the database baggage model.

    Attributes:
    - id (Integer Column): table primary key.
    - weight_lb (Decimal Column): weight of the baggage in lbs.
    - flight_id (Integer Column): foreign key that points to the flights table.
    - compartment_id (Integer Column): foreign key that points to the baggage_compartment table.
    - flight (Relationship): Defines the many-to-one relationship with the flights table.
    - baggage_compartment (Relationship): Defines the many-to-one relationship with 
      the baggage_compartments table.
    """

    __tablename__ = "baggages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(4, 1), nullable=False, default=5.0)
    flight_id = Column(
        Integer,
        ForeignKey(
            "flights.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
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
