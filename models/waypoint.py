"""
Sqlalchemy waypoint model

This module defines the waipoint, aerodrome, and related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class Waypoint(BaseModel):
    """
    This class defines the database waypoints table.
    """

    __tablename__ = "waypoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lat_degrees = Column(Integer, nullable=False)
    lat_minutes = Column(Integer, nullable=False, default=0)
    lat_seconds = Column(Integer, nullable=False, default=0)
    lat_direction = Column(String(1), nullable=False, default="N")
    lon_degrees = Column(Integer, nullable=False)
    lon_minutes = Column(Integer, nullable=False)
    lon_seconds = Column(Integer, nullable=False, default=0)
    lon_direction = Column(String(1), nullable=False, default="E")
    magnetic_variation = Column(
        DECIMAL(precision=3, scale=1),
        nullable=False,
        default=0.0
    )

    vfr_waypoint = Relationship(
        "VfrWaypoint",
        back_populates="waypoint",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    user_waypoint = Relationship(
        "UserWaypoint",
        back_populates="waypoint",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    flight_waypoint = Relationship(
        "FlightWaypoint",
        back_populates="waypoint",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )


class VfrWaypoint(BaseModel):
    """
    This class defines the database vfr_waypoints table.
    """

    __tablename__ = "vfr_waypoints"

    waypoint_id = Column(
        Integer,
        ForeignKey(
            "waypoints.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True,
        nullable=False,
        unique=True
    )
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    hidden = Column(Boolean, nullable=False, default=True)
    creator_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    creator = Relationship("User", back_populates="vfr_waypoints")
    registered_aerodrome = Relationship(
        "Aerodrome",
        back_populates="vfr_waypoint",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    waypoint = Relationship("Waypoint", back_populates="vfr_waypoint")


class UserWaypoint(BaseModel):
    """
    This class defines the database user_waypoints table.
    """

    __tablename__ = "user_waypoints"

    waypoint_id = Column(
        Integer,
        ForeignKey(
            "waypoints.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True,
        nullable=False,
        unique=True
    )
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    creator_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    private_aerodrome = Relationship(
        "Aerodrome",
        back_populates="user_waypoint",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    creator = Relationship("User", back_populates="user_waypoints")
    waypoint = Relationship("Waypoint", back_populates="user_waypoint")


class FlightWaypoint(BaseModel):
    """
    This class defines the database flight_waypoints table.
    """

    __tablename__ = "flight_waypoints"

    waypoint_id = Column(
        Integer,
        ForeignKey(
            "waypoints.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True,
        nullable=False,
        unique=True
    )
    code = Column(String(50), nullable=False)
    leg_id = Column(
        Integer,
        ForeignKey(
            "legs.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    waypoint = Relationship("Waypoint", back_populates="flight_waypoint")
    leg = Relationship("Leg", back_populates="flight_waypoint")


class Aerodrome(BaseModel):
    """
    This class defines the database aerodromes table.
    """

    __tablename__ = "aerodromes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vfr_waypoint_id = Column(
        Integer,
        ForeignKey(
            "vfr_waypoints.waypoint_id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        unique=True
    )
    user_waypoint_id = Column(
        Integer,
        ForeignKey(
            "user_waypoints.waypoint_id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        unique=True
    )
    has_taf = Column(Boolean, nullable=False, default=False)
    has_metar = Column(Boolean, nullable=False, default=False)
    has_fds = Column(Boolean, nullable=False, default=False)
    elevation_ft = Column(Integer, nullable=False, default=0)
    status_id = Column(
        Integer,
        ForeignKey(
            "aerodrome_status.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    vfr_waypoint = Relationship(
        "VfrWaypoint", back_populates="registered_aerodrome")
    user_waypoint = Relationship(
        "UserWaypoint", back_populates="private_aerodrome")
    status = Relationship("AerodromeStatus", back_populates="aerodromes")
    runways = Relationship(
        "Runway",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True
    )
    departures = Relationship(
        "Departure",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True,
        foreign_keys="Departure.aerodrome_id"
    )
    arrivals = Relationship(
        "Arrival",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True,
        foreign_keys="Arrival.aerodrome_id"
    )


class Runway(BaseModel):
    """
    This class defines the database runways table.
    """

    __tablename__ = "runways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    length_ft = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    position = Column(String(1))
    surface_id = Column(
        Integer,
        ForeignKey(
            "runway_surfaces.id",
            ondelete="RESTRICT",
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

    surface = Relationship("RunwaySurface", back_populates="runways")
    aerodrome = Relationship("Aerodrome", back_populates="runways")


class RunwaySurface(BaseModel):
    """
    This class defines the database runway_surfaces table.
    """

    __tablename__ = "runway_surfaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    surface = Column(String(50), nullable=False, unique=True)

    runways = Relationship(
        "Runway",
        back_populates="surface",
        passive_deletes=True,
        passive_updates=True
    )

    aircraft_performance_percentages = Relationship(
        "SurfacePerformanceDecrease",
        back_populates="surface",
        passive_deletes=True,
        passive_updates=True
    )


class AerodromeStatus(BaseModel):
    """
    This class defines the database aerodrome_status table.
    """

    __tablename__ = "aerodrome_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(50), nullable=False, unique=True)

    aerodromes = Relationship(
        "Aerodrome",
        back_populates="status",
        passive_deletes=True,
        passive_updates=True
    )
