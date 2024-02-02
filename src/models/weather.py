"""
Sqlalchemy weather model

This module defines the weather-related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class AerodromeWeatherReport(BaseModel):
    """
    This class defines the database aerodrome_weather_reports table.
    """

    __tablename__ = "aerodrome_weather_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(
        DateTime,
        nullable=False
    )

    departure_id = Column(
        Integer,
        ForeignKey(
            "departures.flight_id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        unique=True,
    )
    arrival_id = Column(
        Integer,
        ForeignKey(
            "arrivals.flight_id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        unique=True,
    )

    departure = Relationship("Departure", back_populates="official_weather")
    arrival = Relationship("Arrival", back_populates="official_weather")

    tafs = Relationship(
        "TafForecast",
        back_populates="aerodrome_weather",
        passive_deletes=True,
        passive_updates=True
    )
    metars = Relationship(
        "MetarReport",
        back_populates="aerodrome_weather",
        passive_deletes=True,
        passive_updates=True
    )


class EnrouteWeatherReport(BaseModel):
    """
    This class defines the database enroute_weather_reports table.
    """

    __tablename__ = "enroute_weather_reports"

    id = Column(
        Integer,
        ForeignKey(
            "legs.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True,
        nullable=False,
        unique=True,
    )
    date = Column(
        DateTime,
        nullable=False
    )

    leg = Relationship("Leg", back_populates="official_weather")

    fds = Relationship(
        "FdForecast",
        back_populates="enroute_weather",
        passive_deletes=True,
        passive_updates=True
    )
    metars = Relationship(
        "MetarReport",
        back_populates="enroute_weather",
        passive_deletes=True,
        passive_updates=True
    )


class TafForecast(BaseModel):
    """
    This class defines the database taf_forecasts table.
    """

    __tablename__ = "taf_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(
        DateTime,
        nullable=False
    )
    date_from = Column(
        DateTime,
        nullable=False
    )
    date_to = Column(
        DateTime,
        nullable=False
    )
    wind_direction = Column(Integer)
    wind_direction_range = Column(Integer)
    wind_magnitude_knot = Column(Integer, nullable=False, default=0)
    gust_factor_knot = Column(Integer)

    aerodrome_weather_id = Column(
        Integer,
        ForeignKey(
            "aerodrome_weather_reports.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aerodrome_id = Column(
        Integer,
        ForeignKey(
            "aerodromes.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aerodrome_weather = Relationship(
        "AerodromeWeatherReport", back_populates="tafs")
    aerodrome = Relationship("Aerodrome", back_populates="tafs")


class MetarReport(BaseModel):
    """
    This class defines the database metar_reports table.
    """

    __tablename__ = "metar_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(
        DateTime,
        nullable=False
    )
    altimeter_inhg = Column(DECIMAL(4, 2), nullable=False)
    temperature_c = Column(Integer)

    aerodrome_weather_id = Column(
        Integer,
        ForeignKey(
            "aerodrome_weather_reports.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
    )
    enroute_weather_id = Column(
        Integer,
        ForeignKey(
            "enroute_weather_reports.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )
    aerodrome_id = Column(
        Integer,
        ForeignKey(
            "aerodromes.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aerodrome_weather = Relationship(
        "AerodromeWeatherReport", back_populates="metars")
    enroute_weather = Relationship(
        "EnrouteWeatherReport", back_populates="metars")
    aerodrome = Relationship("Aerodrome", back_populates="metars")


class FdForecast(BaseModel):
    """
    This class defines the database fd_forecasts table.
    """

    __tablename__ = "fd_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_from = Column(
        DateTime,
        nullable=False
    )
    date_to = Column(
        DateTime,
        nullable=False
    )

    enroute_weather_id = Column(
        Integer,
        ForeignKey(
            "enroute_weather_reports.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    aerodrome_id = Column(
        Integer,
        ForeignKey(
            "aerodromes.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    enroute_weather = Relationship(
        "EnrouteWeatherReport", back_populates="fds")
    aerodrome = Relationship("Aerodrome", back_populates="fds")

    values = Relationship(
        "FdAtAltitude",
        back_populates="forecast",
        passive_deletes=True,
        passive_updates=True
    )


class FdAtAltitude(BaseModel):
    """
    This class defines the database fds_at_altitude table.
    """

    __tablename__ = "fds_at_altitude"

    id = Column(Integer, primary_key=True, autoincrement=True)
    altitude_ft = Column(Integer, nullable=False)
    wind_direction = Column(Integer)
    wind_magnitude_knot = Column(Integer)
    temperature_c = Column(Integer)

    fd_forecasts_id = Column(
        Integer,
        ForeignKey(
            "fd_forecasts.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    forecast = Relationship("FdForecast", back_populates="values")
