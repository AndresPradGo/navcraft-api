"""
Sqlalchemy aircraft model

This module defines the aircraft related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class PerformanceProfile(BaseModel):
    """
    This class defines the database performance_profiles table.
    """

    __tablename__ = "performance_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    is_complete = Column(Boolean)
    center_of_gravity_in = Column(DECIMAL(5, 2))
    empty_weight_lb = Column(DECIMAL(7, 2))
    max_ramp_weight_lb = Column(DECIMAL(7, 2))
    max_landing_weight_lb = Column(DECIMAL(7, 2))
    fuel_arm_in = Column(DECIMAL(5, 2))
    fuel_capacity_gallons = Column(DECIMAL(5, 2))
    unusable_fuel_gallons = Column(DECIMAL(5, 2))
    baggage_allowance_lb = Column(DECIMAL(6, 2))
    take_off_taxi_fuel_gallons = Column(DECIMAL(4, 2))
    percent_decrease_takeoff_headwind_knot = Column(DECIMAL(4, 2))
    percent_increase_takeoff_tailwind_knot = Column(DECIMAL(4, 2))
    percent_decrease_landing_headwind_knot = Column(DECIMAL(4, 2))
    percent_increase_landing_tailwind_knot = Column(DECIMAL(4, 2))
    percent_increase_climb_temperature_c = Column(DECIMAL(4, 2))
    is_preferred = Column(Boolean)
    fuel_type_id = Column(
        Integer,
        ForeignKey(
            "fuel_types.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        )
    )
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )

    aircraft = Relationship(
        "Aircraft", back_populates="performance_profiles")
    fuel_type = Relationship("FuelType", back_populates="performance_profiles")
    baggage_compartments = Relationship(
        "BaggageCompartment",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    seat_rows = Relationship(
        "SeatRow",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    performance_decreace_runway_surfaces = Relationship(
        "SurfacePerformanceDecrease",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    weight_balance_profiles = Relationship(
        "WeightBalanceProfile",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    takeoff_performance_data = Relationship(
        "TakeoffPerformance",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    landing_performance_data = Relationship(
        "LandingPerformance",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    climb_performance_data = Relationship(
        "ClimbPerformance",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    cruise_performance_data = Relationship(
        "CruisePerformance",
        back_populates="performance_profile",
        passive_deletes=True,
        passive_updates=True
    )


class Aircraft(BaseModel):
    """
    This class defines the database aircraft table.
    """

    __tablename__ = "aircraft"

    id = Column(Integer, primary_key=True, autoincrement=True)
    make = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    abbreviation = Column(String(10), nullable=False)
    registration = Column(String(50), nullable=False)
    owner_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    performance_profiles = Relationship(
        "PerformanceProfile",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    owner = Relationship("User", back_populates="aircraft")
    flights = Relationship(
        "Flight",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )


class SurfacePerformanceDecrease(BaseModel):
    """
    This class defines the database surface_performance_decrease table.
    """

    __tablename__ = "surfaces_performance_decrease"

    id = Column(Integer, primary_key=True, autoincrement=True)
    percent = Column(DECIMAL(4, 2), nullable=False, default=0)
    is_takeoff = Column(Boolean, nullable=False, default=True)
    surface_id = Column(
        Integer,
        ForeignKey(
            "runway_surfaces.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    surface = Relationship(
        "RunwaySurface", back_populates="aircraft_performance_percentages")
    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="performance_decreace_runway_surfaces"
    )


class WeightBalanceProfile(BaseModel):
    """
    This class defines the database weight_balance_profiles table.
    """

    __tablename__ = "weight_balance_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="Normal Category")
    max_take_off_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="weight_balance_profiles"
    )
    weight_balance_limits = Relationship(
        "WeightBalanceLimit",
        back_populates="weight_balance_profile",
        passive_deletes=True,
        passive_updates=True
    )


class WeightBalanceLimit(BaseModel):
    """
    This class defines the database weight_balance_limits table.
    """

    __tablename__ = "weight_balance_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_cg_in = Column(DECIMAL(5, 2), nullable=False)
    from_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    to_cg_in = Column(DECIMAL(5, 2), nullable=False)
    to_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    weight_balance_profile_id = Column(
        Integer,
        ForeignKey(
            "weight_balance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    weight_balance_profile = Relationship(
        "WeightBalanceProfile",
        back_populates="weight_balance_limits"
    )


class BaggageCompartment(BaseModel):
    """
    This class defines the database baggage_compartments table.
    """

    __tablename__ = "baggage_compartments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    arm_in = Column(DECIMAL(5, 2), nullable=False)
    weight_limit_lb = Column(DECIMAL(6, 2))
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="baggage_compartments"
    )

    baggages = Relationship(
        "Baggage",
        back_populates="baggage_compartment",
        passive_deletes=True,
        passive_updates=True
    )


class SeatRow(BaseModel):
    """
    This class defines the database seat_rows table.
    """

    __tablename__ = "seat_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    arm_in = Column(DECIMAL(5, 2), nullable=False)
    weight_limit_lb = Column(DECIMAL(6, 2))
    number_of_seats = Column(Integer, nullable=False)
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="seat_rows"
    )
    passengers = Relationship(
        "Passenger",
        back_populates="seat_row",
        passive_deletes=True,
        passive_updates=True
    )


class TakeoffLandingPerformance(BaseModel):
    """
    This class defines the database takeoff and landing performance base model, 
    which will be the parent for the TakeoffPerformance and LandingPerformance models.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(Integer, nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    groundroll_ft = Column(Integer, nullable=False)
    obstacle_clearance_ft = Column(Integer, nullable=False)
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )


class TakeoffPerformance(TakeoffLandingPerformance):
    """
    This class defines the database takeoff_performance_data table.
    """

    __tablename__ = "takeoff_performance_data"

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="takeoff_performance_data"
    )


class LandingPerformance(TakeoffLandingPerformance):
    """
    This class defines the database landing_performance model.
    """

    __tablename__ = "landing_performance_data"

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="landing_performance_data"
    )


class ClimbPerformance(BaseModel):
    """
    This class defines the database climb_performance_data table.
    """

    __tablename__ = "climb_performance_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(Integer, nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    kias = Column(Integer)
    fpm = Column(Integer)
    time_min = Column(Integer, nullable=False)
    fuel_gal = Column(DECIMAL(4, 2), nullable=False)
    distance_nm = Column(Integer, nullable=False)
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="climb_performance_data"
    )


class CruisePerformance(BaseModel):
    """
    This class defines the database cruise_performance_data table.
    """

    __tablename__ = "cruise_performance_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(Integer, nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    bhp_percent = Column(Integer, nullable=False)
    rpm = Column(Integer, nullable=False)
    ktas = Column(Integer, nullable=False)
    gph = Column(DECIMAL(6, 2), nullable=False)
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="cruise_performance_data"
    )


class FuelType(BaseModel):
    """
    This class defines the database fuel_types table.
    """

    __tablename__ = "fuel_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    density_lb_gal = Column(DECIMAL(4, 2), nullable=False)

    performance_profiles = Relationship(
        "PerformanceProfile",
        back_populates="fuel_type",
        passive_deletes=True,
        passive_updates=True
    )
