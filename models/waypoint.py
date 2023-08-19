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
    - code (String Column): waypoint code identifyer.
    - name (String Column): waypoint name.
    - is_official (boolean Column): True if waypoint is an official aviation waypoint.
    - lat_degrees (Integer Column): latitude degrees of the waypoint coordinates.
    - lat_minutes (Integer Column): latitude minutes of the waypoint coordinates.
    - lat_seconds (Integer Column): latitude seconds of the waypoint coordinates.
    - lat_direction (String Column): latitude direction of the waypoint coordinates ("N" or "S").
    - lon_degrees (Integer Column): longitude degrees of the waypoint coordinates.
    - lon_minutes (Integer Column): longitude minutes of the waypoint coordinates.
    - lon_seconds (Integer Column): longitude seconds of the waypoint coordinates.
    - lon_direction (String Column): longitude direction of the waypoint coordinates ("E" or "W").
    - magnetic_variation (Decimal Column): magnetic variation at the waypoint.
    - aerodrome (Relationship): Defines the one-to-one relationship with the Aerodrome table.
    - legs (Relationship): defines the one-to-many relationship with the Leg table.
    """

    __tablename__ = "waypoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    is_official = Column(Boolean, nullable=False, default=True)
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

    aerodrome = Relationship(
        "Aerodrome",
        back_populates="waypoint",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    legs = Relationship(
        "Leg",
        back_populates="waypoint",
        passive_deletes=True,
        passive_updates=True
    )


class Aerodrome(BaseModel):
    """
    This class defines the database aerodrome model.

    Attributes:
    - id (Integer Column): table primary key. Also a foreignkey with the waypoints table.
    - has_taf (Boolean Column): True if the aerodrome has an official TAF.
    - has_metar(Boolean Column): True if the aerodrome has an official METAR.
    - has_fds (Boolean Column): True if the aerodrome has an official FDs.
    - elevation (Integer Column): aerodrome elevation in feet.
    - waypoint (Relationship): defines the one-to-one relationship with the waypoints table.
    - runways (Relationship): list of runways.
    """

    __tablename__ = "aerodromes"

    id = Column(
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
    has_taf = Column(Boolean, nullable=False, default=False)
    has_metar = Column(Boolean, nullable=False, default=False)
    has_fds = Column(Boolean, nullable=False, default=False)
    elevation = Column(Integer, nullable=False, default=0)

    waypoint = Relationship("Waypoint", back_populates="aerodrome")
    runways = Relationship(
        "Runway",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True
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
    - departures (Relationship): defines the one_to_many relationship with the departures table.
    - arrivals (Relationship): defines the one_to_many relationship with the arrivals table.
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
        nullable=False,
        unique=True
    )

    surface = Relationship("RunwaySurface", back_populates="runways")
    aerodrome = Relationship("Aerodrome", back_populates="runways")
    departures = Relationship(
        "Departure",
        back_populates="runway",
        passive_deletes=True,
        passive_updates=True,
        foreign_keys="Departure.runway_id"
    )
    arrivals = Relationship(
        "Arrival",
        back_populates="runway",
        passive_deletes=True,
        passive_updates=True,
        foreign_keys="Arrival.runway_id"
    )


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
    performance_level = Column(Integer, nullable=False, autoincrement=True)

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
