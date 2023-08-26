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
    This class defines the database waypoint model.

    Attributes:
    - id (Integer Column): table primary key.
    - lat_degrees (Integer Column): latitude degrees of the waypoint coordinates.
    - lat_minutes (Integer Column): latitude minutes of the waypoint coordinates.
    - lat_seconds (Integer Column): latitude seconds of the waypoint coordinates.
    - lat_direction (String Column): latitude direction of the waypoint coordinates ("N" or "S").
    - lon_degrees (Integer Column): longitude degrees of the waypoint coordinates.
    - lon_minutes (Integer Column): longitude minutes of the waypoint coordinates.
    - lon_seconds (Integer Column): longitude seconds of the waypoint coordinates.
    - lon_direction (String Column): longitude direction of the waypoint coordinates ("E" or "W").
    - magnetic_variation (Decimal Column): magnetic variation at the waypoint.
    - vfr_waypoint (Relationship): defines the one-to-one relationship with the vfr_waypoints child-table.
    - user_waypoint (Relationship): defines the one-to-one relationship with the user_waypoints child-table.
    - flight_waypoint (Relationship): defines the one-to-one relationship with the flight_waypoints child-table.
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
    This class defines the database vfr_waypoint model.

    Attributes:
    - waypoint_id (Integer Column): table primary key. Also a foreignkey with the waypoints table.
    - creator_id (Integer Column): foreign key that points to the users table.
    - creator (Relationship): defines the many-to-one relationship with the users table.
    - aerodrome (Relationship): Defines the one-to-one relationship with the Aerodrome table.
    - waypoint (Relationship): defines the one-to-one relationship with the waypoints parent-table.
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
    aerodrome = Relationship(
        "Aerodrome",
        back_populates="vfr_waypoint",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    waypoint = Relationship("Waypoint", back_populates="vfr_waypoint")


class UserWaypoint(BaseModel):
    """
    This class defines the database user_waypoint model.

    Attributes:
    - waypoint_id (Integer Column): table primary key. Also a foreignkey with the waypoints table.
    - code (String Column): waypoint code identifyer.
    - name (String Column): waypoint name.
    - creator_id (Integer Column): foreign key that points to the users table.
    - creator (Relationship): defines the many-to-one relationship with the users table.
    - waypoint (Relationship): defines the one-to-one relationship with the waypoints parent-table.
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
    code = Column(String(50), nullable=False, unique=True)
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

    creator = Relationship("User", back_populates="user_waypoints")
    waypoint = Relationship("Waypoint", back_populates="user_waypoint")


class FlightWaypoint(BaseModel):
    """
    This class defines the database flight_waypoint model.

    Attributes:
    - waypoint_id (Integer Column): table primary key. Also a foreignkey with the waypoints table.
    - code (String Column): waypoint code identifyer.
    - leg_id (Integer Column): 
    - waypoint (Relationship): defines the one-to-one relationship with the waypoints parent-table.
    - leg (Relationship): defines the one-to-one relationship with the legs parent-table.
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
    code = Column(String(50), nullable=False, unique=True)
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
    This class defines the database aerodrome model.

    Attributes:
    - waypoint_id (Integer Column): table primary key. Also a foreignkey with the waypoints table.
    - has_taf (Boolean Column): True if the aerodrome has an official TAF.
    - has_metar(Boolean Column): True if the aerodrome has an official METAR.
    - has_fds (Boolean Column): True if the aerodrome has an official FDs.
    - elevation_ft (Integer Column): aerodrome elevation in feet.
    - status_id (Integer Column): foreignkey with the aerodrome_status table.
    - vfr_waypoint (Relationship): defines the one-to-one relationship with the waypoints table.
    - runways (Relationship): list of runways.
    - departures (Relationship): defines the one_to_many relationship with the departures table.
    - arrivals (Relationship): defines the one_to_many relationship with the arrivals table.
    - status (Relationship): defines the many-to-one relationship with the aerodrome_status table.
    """

    __tablename__ = "aerodromes"

    vfr_waypoint_id = Column(
        Integer,
        ForeignKey(
            "vfr_waypoints.waypoint_id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        primary_key=True,
        nullable=False,
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

    vfr_waypoint = Relationship("VfrWaypoint", back_populates="aerodrome")
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
    This class defines the database runway model.

    Attributes:
    - id (Integer Column): table primary key.
    - length_ft (Integer Column): length of the runway in ft.
    - number (integer Column): runway number.
    - position (String Column): "R", "L" or "C" position for parallel runways.
    - surface_id (Integer Column): foreign key that points to the runway_surfaces table.
    - aerodrome_id (Integer Column): foreign key that points to the aerodromes table.
    - surface (Relationship): defines the many-to-one relationship with the runway_surfaces table.
    - aerodrome (Relationship): Defines the one-to-one relationship with the aerodromes table.
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
            "aerodromes.vfr_waypoint_id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False,
        unique=True
    )

    surface = Relationship("RunwaySurface", back_populates="runways")
    aerodrome = Relationship("Aerodrome", back_populates="runways")


class RunwaySurface(BaseModel):
    """
    This class defines the database runway_surface model.

    Attributes:
    - id (Integer Column): table primary key.
    - surface (String Column): runway surface material.
    - performance_level (Integer Column): sorts the surfaces in terms of which one is better; 
      e.g. if asphalt has a performance_level of 1, grass has a performance level of 2, since 
      aircraft performe better on asphalt.
    - runways (Relationship): defines the one_to_many relationship with the runways table.
    - aircraft_performance_percentages (Relationship): defines the one_to_many relationship 
      with the surfaces_performance_decrease table.
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
    This class defines the database aerodrome_status model.

    Attributes:
    - id (Integer Column): table primary key.
    - status (String Column): the aerodrome status (e.g. saved, printed, completed)
    - aerodromes (Relationship): list of aerodromes with the status.
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
