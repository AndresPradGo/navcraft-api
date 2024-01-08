"""
Sqlalchemy waypoint model

This module defines the waipoint, aerodrome, and related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

import math
from typing import Union, List

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
    in_north_airspace = Column(Boolean, nullable=False, default=False)

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
        """
        direction = {"N": 1, "S": -1}

        lat_degrees = direction[self.lat_direction] * \
            (self.lat_degrees + self.lat_minutes / 60 + self.lat_seconds / 3600)

        return math.radians(lat_degrees)

    def lon(self) -> float:
        """
        This method returns the longitude of the waypoint in radians.
        """
        direction = {"E": 1, "W": -1}

        lon_degrees = direction[self.lon_direction] * \
            (self.lon_degrees + self.lon_minutes / 60 + self.lon_seconds / 3600)

        return math.radians(lon_degrees)

    def cartesian_coordinates_nm(self, unit_vector: bool = False) -> List[float]:
        """
        This method returns the cartesian coordinates of the waypoint in nautical miles.
        """

        earth_radius = 1 if unit_vector else get_constant("earth_radius_ft")\
            * get_constant("ft_to_nautical")

        return [earth_radius * math.cos(self.lat()) * math.cos(self.lon()),
                earth_radius * math.cos(self.lat()) * math.sin(self.lon()),
                earth_radius * math.sin(self.lat())]

    def great_arc_to(self, to_lat: float, to_lon: float) -> float:
        """
        This method finds the distance of a great arc from self, 
        to a given latitude and longitude, in nautical miles.
        """
        earth_radius = get_constant("earth_radius_ft")\
            * get_constant("ft_to_nautical")

        # Cartesian coordinates
        cartesian_from = np.array(self.cartesian_coordinates_nm())
        cartesian_to = np.array([
            earth_radius * math.cos(to_lat) *
            math.cos(to_lon),
            earth_radius * math.cos(to_lat) *
            math.sin(to_lon),
            earth_radius * math.sin(to_lat)
        ])

        distance = round(
            earth_radius *
            np.arccos(np.clip(np.dot(cartesian_from, cartesian_to) /
                      earth_radius**2, -1.0, 1.0)),
            0
        )

        return distance

    def great_arc_to_waypoint(self, to_waypoint: 'Waypoint') -> float:
        """
        This method finds the distance of a great arc from self, 
        to another waypoint, in nautical miles.
        """

        return self.great_arc_to(to_waypoint.lat(), to_waypoint.lon())

    def true_track_to(self, to_lat: float, to_lon: float, precise: bool = False) -> Union[int, float]:
        """
        This method finds the true track from self, 
        to a given latitude and longitude, in degrees.
        If precise is false, it rounds it to the neares degree.
        """

        earth_radius = get_constant(
            "earth_radius_ft") * get_constant("ft_to_nautical")

        # Calculate differences in latitude and longitude
        from_waypoint = np.array(self.cartesian_coordinates_nm())
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
        track = math.degrees(np.arccos(np.clip(np.dot(n_plain1, n_plain2), -1.0, 1.0))) if is_easterly\
            else 360 - math.degrees(np.arccos(np.clip(np.dot(n_plain1, n_plain2), -1.0, 10.)))

        return track if precise else int(round(track, 0))

    def true_track_to_waypoint(self, to_waypoint: 'Waypoint', precise: bool = False) -> int:
        """
        This method finds the true track from self, 
        to another waypoint, in degrees.
        """
        return self.true_track_to(to_waypoint.lat(), to_waypoint.lon(), precise)

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
        """

        if self.magnetic_variation is not None\
                and other_waypoint.magnetic_variation is not None:
            return (float(self.magnetic_variation) + float(other_waypoint.magnetic_variation)) / 2
        if self.magnetic_variation is not None:
            return float(self.magnetic_variation)
        if other_waypoint.magnetic_variation is not None:
            return float(other_waypoint.magnetic_variation)
        return 0.0

    def find_rotation_matrix(self, to_waypoint: 'Waypoint'):
        """
        This method returns the rotation matrix to rotate from an eatch-centered coordinate system, 
        to a coordinate system where the positive x-axis points towards the true track from waypoint_1
        to to_waypoint.
        """
        rad_90 = np.radians(90)
        angle_1 = self.lon() + rad_90
        angle_2 = rad_90 - self.lat()
        angle_3 = np.radians(
            90 - self.true_track_to_waypoint(to_waypoint=to_waypoint, precise=True))

        rotation_z = np.array([
            [np.cos(angle_1), np.sin(angle_1), 0],
            [-np.sin(angle_1), np.cos(angle_1), 0],
            [0, 0, 1]
        ])

        rotation_x_1 = np.array([
            [1, 0, 0],
            [0, np.cos(angle_2), np.sin(angle_2)],
            [0, -np.sin(angle_2), np.cos(angle_2)]
        ])

        rotation_z_2 = np.array([
            [np.cos(angle_3), np.sin(angle_3), 0],
            [-np.sin(angle_3), np.cos(angle_3), 0],
            [0, 0, 1]
        ])

        rotation_total = np.dot(rotation_z_2, np.dot(rotation_x_1, rotation_z))
        return rotation_total

    def find_halfway_coordinates(self, to_waypoint: 'Waypoint') -> List[float]:
        """
        This method finds the coordinates of the point halfway between self and to_waypoint, 
        in radians, and returns them in a list of [Latitude, Longitude].
        """

        return [(self.lat() + to_waypoint.lat())/2, (self.lon() + to_waypoint.lon())/2]

    def find_interval_coordinates(self, to_waypoint: 'Waypoint', distance_interval_nm: int) -> List[List[float]]:
        """
        This method finds the list of coordinates, in radians of [Latitude, Longitude], 
        of the points over the track between self and to_waypoint, in a given intervals of separation.
        """

        R_matrix = self.find_rotation_matrix(to_waypoint)
        R_inverse = np.transpose(R_matrix)
        total_distance = self.great_arc_to_waypoint(to_waypoint=to_waypoint)
        n_total = math.ceil(total_distance/distance_interval_nm)
        current_distance = distance_interval_nm
        cartesian_linear_position = np.dot(
            R_matrix, np.array(self.cartesian_coordinates_nm()))
        coordinate_list = [[self.lat(), self.lon()]]

        while current_distance < total_distance:
            cartesian_linear_position += np.array([distance_interval_nm, 0, 0])

            # Rotate back to earth-centered system
            cartesian_position = np.dot(R_inverse, cartesian_linear_position)
            r = np.linalg.norm(cartesian_position)
            longitude = np.arctan2(
                cartesian_position[1], cartesian_position[0])
            latitude = np.radians(
                90) - np.arccos(np.clip(cartesian_position[2] / r, -1.0, 1.0))

            coordinate_list.append([latitude, longitude])

            current_distance += distance_interval_nm

        return coordinate_list

    def is_in_northern_airspace(self):
        """
        This method finds if the waypoint is in the Northern Domestic Airspace
        """
        # Function to convert from coordinate to cartesian unit np array
        def to_cartesian_array(lat: List[int], lon: List[int]):
            lat_rad = np.radians(lat[0] + (lat[1] + lat[2] / 60) / 60)
            lon_rad = np.radians(lon[0] + (lon[1] + lon[2] / 60) / 60)

            return np.array([math.cos(lat_rad) * math.cos(lon_rad),
                             math.cos(lat_rad) * math.sin(lon_rad),
                             math.sin(lat_rad)])

        # Define constants
        epsilon = 1e-9
        ceil_lat = np.radians(72)
        floor_lat = np.radians(58 + 46/60)
        ref_point = to_cartesian_array(lat=[80, 0, 0], lon=[-90, -0, -0])
        boundary_points = [
            to_cartesian_array(lat=[69, 0, 0], lon=[-141, -0, -0]),
            to_cartesian_array(lat=[72, 0, 0], lon=[-129, -0, -0]),
            to_cartesian_array(lat=[67, 40, 22], lon=[-129, -29, -34]),
            to_cartesian_array(lat=[63, 11, 21], lon=[-115, -19, -22]),
            to_cartesian_array(lat=[62, 10, 55], lon=[-112, -45, -20]),
            to_cartesian_array(lat=[59, 0, 30], lon=[-95, -29, -15]),
            to_cartesian_array(lat=[58, 46, 0], lon=[-92, -21, -0]),
            to_cartesian_array(lat=[62, 6, 47], lon=[-79, -11, -59]),
            to_cartesian_array(lat=[62, 34, 13], lon=[-76, -31, -52]),
            to_cartesian_array(lat=[63, 26, 30], lon=[-69, -53, -30]),
            to_cartesian_array(lat=[64, 14, 23], lon=[-67, -34, -28]),
            to_cartesian_array(lat=[67, 31, 57], lon=[-60, -18, -13]),
        ]
        boundary_arcs = [
            {
                "lat": math.radians(62 + (27 + 52/60)/60),
                "lon": math.radians(-114 - (26 + 12/60)/60),
                "radius": 50
            },
            {
                "lat": math.radians(58 + (45 + 45/60)/60),
                "lon": math.radians(-93 - (57 + 14/60)/60),
                "radius": 50
            },
            {
                "lat": math.radians(62 + (24 + 49/60)/60),
                "lon": math.radians(-77 - (55 + 38/60)/60),
                "radius": 40
            },
            {
                "lat": math.radians(63 + (44)/60),
                "lon": math.radians(-68 - (32 + 53/60)/60),
                "radius": 40
            },
        ]

        # Find if waypoint is above ceil or below floor
        if self.lat() > ceil_lat:
            return True
        if self.lat() < floor_lat:
            return False

        # Find if waypoint is within radius of arc segments of the NDA boundary
        for arc in boundary_arcs:
            if self.great_arc_to(to_lat=arc["lat"], to_lon=arc["lon"]) <= arc['radius']:
                return False

        # Find if waypoint is north of the boundary
        waypoint = np.array(self.cartesian_coordinates_nm(unit_vector=True))
        i = 0
        while i < len(boundary_points) - 1:
            boundary_p1 = boundary_points[i]
            boundary_p2 = boundary_points[i + 1]
            normal_1 = np.cross(waypoint, ref_point)
            normal_2 = np.cross(boundary_p1, boundary_p2)
            intersect_vector = np.cross(normal_1, normal_2)
            intersect_1 = intersect_vector / np.linalg.norm(intersect_vector)
            intersect_2 = -intersect_1

            for intersect in [intersect_1, intersect_2]:
                arcs_intersect = True
                for arc in [[waypoint, ref_point], [boundary_p1, boundary_p2]]:
                    theta_1_to_intersect = np.arccos(np.dot(
                        arc[0], intersect) / (np.linalg.norm(arc[0]) * np.linalg.norm(intersect)))
                    theta_2_to_intersect = np.arccos(np.dot(
                        arc[1], intersect) / (np.linalg.norm(arc[1]) * np.linalg.norm(intersect)))
                    theta_1_to_2 = np.arccos(
                        np.dot(arc[0], arc[1]) / (np.linalg.norm(arc[0]) * np.linalg.norm(arc[1])))
                    arcs_intersect = arcs_intersect and (
                        abs(theta_1_to_2 - theta_1_to_intersect - theta_2_to_intersect) <= epsilon)
                if arcs_intersect:
                    return False
            i += 1

        return True


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
    code = Column(String(12), nullable=False, unique=True)
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
    code = Column(String(12), nullable=False)
    name = Column(String(50), nullable=False)
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
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        primary_key=True,
        nullable=False,
        unique=True
    )
    code = Column(String(12), nullable=False)
    name = Column(String(50), nullable=False)
    from_user_waypoint = Column(Boolean, nullable=False, default=False)
    from_vfr_waypoint = Column(Boolean, nullable=False, default=False)
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
    tafs = Relationship(
        "TafForecast",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True,
    )
    metars = Relationship(
        "MetarReport",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True,
    )
    fds = Relationship(
        "FdForecast",
        back_populates="aerodrome",
        passive_deletes=True,
        passive_updates=True,
    )


class Runway(BaseModel):
    """
    This class defines the database runways table.
    """

    __tablename__ = "runways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    length_ft = Column(Integer, nullable=False)
    landing_length_ft = Column(Integer, nullable=False)
    intersection_departure_length_ft = Column(Integer)
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
