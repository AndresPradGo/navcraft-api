"""
Sqlalchemy waypoint model

This module defines the waipoint, aerodrome, and related db-table models.

Usage: 
- Import the required model classto create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class Waypoint(BaseModel):
    """
    This class defines the database waypoint model.

    Attributes:
    - id (Integer Column): table row entry id.
    - code (String Column): waypoint code identifyer.
    - name (String Column): waypoint name.
    - user_added (boolean Column): True if waypoint was added by a normal user, 
                                   False if it was added by an admin user.
    - lat_degrees (Integer Column): latitude degrees of the waypoint coordinates.
    - lat_minutes (Integer Column): latitude minutes of the waypoint coordinates.
    - lat_seconds (Integer Column): latitude seconds of the waypoint coordinates.
    - lat_direction (String Column): latitude direction of the waypoint coordinates ("N" or "S").
    - lon_degrees (Integer Column): longitude degrees of the waypoint coordinates.
    - lon_minutes (Integer Column): longitude minutes of the waypoint coordinates.
    - lon_seconds (Integer Column): longitude seconds of the waypoint coordinates.
    - lon_direction (String Column): longitude direction of the waypoint coordinates ("E" or "W").
    - aerodrome (Relationship): Defines the one-to-one relationship with the Aerodrome table.
    - legs (Relationship): defines the one-to-many relationship with the Leg table.
    """

    __tablename__ = "waypoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    user_added = Column(Boolean, nullable=False, default=True)
    lat_degrees = Column(Integer, nullable=False)
    lat_minutes = Column(Integer, nullable=False)
    lat_seconds = Column(Integer, nullable=False, default=0)
    lat_direction = Column(String(1), nullable=False, default="N")
    lon_degrees = Column(Integer, nullable=False)
    lon_minutes = Column(Integer, nullable=False)
    lon_seconds = Column(Integer, nullable=False, default=0)
    lon_direction = Column(String(1), nullable=False, default="E")

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
    - id (Integer Column): table row entry id.
    - elevation (Integer Column): aerodrome elevation in feet.
    - status_id (Integer Column): foreign key that defines the relation with the aerodrome_status table.
    - status (Relationship): defines the many_to_one relationship, with the aerodrome_status table.
    - waypoint (Relationship): defines the one_to_one relationship, with the waypoints table.
    - runways (Relationship): defines the one_to_many relationship, with the runways table.
    - departure_point_trips (Relationship): defines the one_to_many relationship, with the trips table.
                                            List of trips for which an aerodrome has been the departure point.
    - destination_point_trips (Relationship): defines the one_to_many relationship, with the runways table.
                                              List of trips for which an aerodrome has been the destination point.
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
    elevation = Column(Integer, nullable=False, default=0)
    status_id = Column(
        Integer,
        ForeignKey(
            "aerodrome_status.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        nullable=False,
        default=1
    )

    status = Relationship("AerodromeStatus", back_populates="aerodrome")
    waypoint = Relationship(
        "Waypoint",
        back_populates="aerodrome",
        foreign_keys=[id]
    )
    runways = Relationship(
        "Runway",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True
    )
    departure_point_trips = Relationship(
        "Trip",
        back_populates="departure",
        passive_deletes=True,
        passive_updates=True,
        foreign_keys="Trip.departure_id"
    )
    destination_point_trips = Relationship(
        "Trip",
        back_populates="destination",
        passive_deletes=True,
        passive_updates=True,
        foreign_keys="Trip.destination_id"
    )


class Runway(BaseModel):
    """
    This class defines the database runway model.

    Attributes:
    - id (Integer Column): table row entry id.
    - length_ft (Integer Column): length of the runway in ft.
    - number (integer Column): runway number.
    - position (String Column): "R", "L" or "C" position for parallel runways.
    - surface_id (Integer Column): foreign key that defines the relation with the runway_surfaces table.
    - aerodrome_id (Integer Column): foreign key that defines the relation with the aerodromes table.
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
            "aerodromes.id",
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
    - id (Integer Column): table row entry id.
    - surface (String Column): runway surface material.
    - runways (Relationship): defines the one_to_many relationship with the runways table.
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


class AerodrometStatus(BaseModel):
    """
    This class defines the database aerodrome_status model.

    Attributes:
    - id (Integer Column): table row entry id.
    - status (String Column): aerodrome status.
    - aerodrome (Relationship): defines the one_to_many relationship with the aerodromes table.
    """

    __tablename__ = "aerodrome_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(50), nullable=False, unique=True)

    aerodrome = Relationship(
        "Aerodrome",
        back_populates="status",
        passive_deletes=True,
        passive_updates=True
    )
