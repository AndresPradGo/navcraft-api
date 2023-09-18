"""
Sqlalchemy waypoint model

This module defines the waipoint, aerodrome, and related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

import math

import numpy as np
from sqlalchemy import Column, Integer, DECIMAL, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel

from utils.config import get_constant


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
    magnetic_variation = Column(DECIMAL(4, 2))

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

    def lat(self) -> float:
        """
        This method returns the latitude of the waypoint in radians.

        Parameters: None

        Returns: 
        - float: Latitude in radians.
        """
        direction = {"N": 1, "S": -1}

        lat_degrees = direction[self.lat_direction] * \
            (self.lat_degrees + self.lat_minutes / 60 + self.lat_seconds / 120)

        return math.radians(lat_degrees)

    def lon(self) -> float:
        """
        This method returns the longitude of the waypoint in radians.

        Parameters: None

        Returns: 
        - float: longitude in radians.
        """
        direction = {"E": 1, "W": -1}

        lon_degrees = direction[self.lon_direction] * \
            (self.lon_degrees + self.lon_minutes / 60 + self.lon_seconds / 120)

        return math.radians(lon_degrees)

    def great_arc_to(self, to_lat: float, to_lon: float) -> float:
        """
        This method finds the distance of a great arc from self, 
        to a given latitude and longitude, in nautical miles.

        Parameters: 
        to_lat (float): latitude of destination.
        to_lon (float): latitude of destination.

        Returns: 
        - float: great arc distance in nautical miles.
        """
        earth_radius = get_constant("earth_radius_ft")\
            * get_constant("ft_to_nm")

        # Cartesian coordinates
        cartesian_from = np.array([
            earth_radius * math.cos(self.lat()) * math.cos(self.lon()),
            earth_radius * math.cos(self.lat()) * math.sin(self.lon()),
            earth_radius * math.sin(self.lat())
        ])
        cartesian_to = np.array([
            earth_radius * math.cos(to_lat) *
            math.cos(to_lon),
            earth_radius * math.cos(to_lat) *
            math.sin(to_lon),
            earth_radius * math.sin(to_lat)
        ])

        return round(
            earth_radius *
            math.acos(np.dot(cartesian_from, cartesian_to) / earth_radius**2),
            2
        )

    def great_arc_to_waypoint(self, to_waypoint: 'Waypoint') -> float:
        """
        This method finds the distance of a great arc from self, 
        to another waypoint, in nautical miles.

        Parameters: 
        to_waypoint (Waypoint): destination waypoint.

        Returns: 
        - float: great arc distance in nautical miles.
        """

        return self.great_arc_to(to_waypoint.lat(), to_waypoint.lon())

    def true_track_to(self, to_lat: float, to_lon: float) -> int:
        """
        This method finds the true track from self, 
        to a given latitude and longitude, in degrees.

        Parameters: 
        to_lat (float): latitude of destination.
        to_lon (float): latitude of destination.

        Returns: 
        - int: true track in degrees.
        """

        earth_radius = get_constant(
            "earth_radius_ft") * get_constant("ft_to_nm")

        # Calculate differences in latitude and longitude
        from_waypoint = np.array([
            earth_radius * math.cos(self.lat()) * math.cos(self.lon()),
            earth_radius * math.cos(self.lat()) * math.sin(self.lon()),
            earth_radius * math.sin(self.lat())
        ])
        to_waypoint = np.array([
            earth_radius * math.cos(to_lat) * math.cos(to_lon),
            earth_radius * math.cos(to_lat) * math.sin(to_lon),
            earth_radius * math.sin(to_lat)
        ])

        delta_lon = to_lon - self.lon()
        if delta_lon > math.pi:
            delta_lon -= 2 * math.pi
        elif delta_lon < -math.pi:
            delta_lon += 2 * math.pi
        halfway_lon = delta_lon / 2 + self.lon()

        half_waypoint = np.array([
            earth_radius * math.cos(halfway_lon),
            earth_radius * math.sin(halfway_lon), 0
        ])
        north = np.array([0, 0, earth_radius])

        normal_plain1 = np.cross(from_waypoint, to_waypoint)
        normal_plain2 = np.cross(half_waypoint, north)

        n_plain1 = normal_plain1 / np.linalg.norm(normal_plain1)\
            if np.linalg.norm(normal_plain1) > 1e-9\
            else normal_plain1
        n_plain2 = normal_plain2 / np.linalg.norm(normal_plain2)\
            if np.linalg.norm(normal_plain2) > 1e-9\
            else normal_plain2

        is_easterly = delta_lon > 0
        track = math.degrees(math.acos(np.dot(n_plain1, n_plain2))) if is_easterly\
            else 360 - math.degrees(math.acos(np.dot(n_plain1, n_plain2)))

        return int(round(track, 0))

    def true_track_to_waypoint(self, to_waypoint: 'Waypoint') -> int:
        """
        This method finds the true track from self, 
        to another waypoint, in degrees.

        Parameters: 
        to_waypoint (Waypoint): destination waypoint.

        Returns: 
        - int: true track in degrees.
        """
        return self.true_track_to(to_waypoint.lat(), to_waypoint.lon())

    def is_equal(self, other_waypoint: 'Waypoint') -> bool:
        """
        This method returns true if self and another waypoint are within 0.5 NM of eachother

        Parameters: 
        other_waypoint (Waypoint): other waypoint.

        Returns: 
        - int: true if both waypoints are located within 0.5 NM of eachother.
        """

        return self.great_arc_to_waypoint(to_waypoint=other_waypoint) < 0.5

    def get_magnetic_var(self, other_waypoint: 'Waypoint') -> float:
        """
        This method returns the magnetic variation between 2 points:
         - If both have magnetic variation, it returns the average.
         - If only one has magnetic variation, it returns that one.
         - If none have magnetic variaiton it returns 0.

        Parameters: 
        other_waypoint (Waypoint): other waypoint.

        Returns: 
        - float: magnetic variation.
        """

        if self.magnetic_variation is not None\
                and other_waypoint.magnetic_variation is not None:
            return (float(self.magnetic_variation) + float(other_waypoint.magnetic_variation)) / 2
        if self.magnetic_variation is not None:
            return float(self.magnetic_variation)
        if other_waypoint.magnetic_variation is not None:
            return float(other_waypoint.magnetic_variation)
        return 0.0


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
