"""
Sqlalchemy aircraft model

This module defines the aircraft related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class AircraftMake(BaseModel):
    """
    This class defines the database aircraft_makes table.

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): aircraft manufacturer name.
    - models (Relationship): defines the one-to-many relationship with the aircraft_moel child table.
    """

    __tablename__ = "aircraft_makes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)

    models = Relationship(
        "AircraftModel",
        back_populates="make",
        passive_deletes=True,
        passive_updates=True
    )


class AircraftModel(BaseModel):
    """
    This class defines the database aircraft_models table.

    Attributes:
    - id (Integer Column): table primary key.
    - model (String Column): aircraft model (e.g. Cessna 172 SR Long Range).
    - code (String Column): aircraft code that identifies the aircraft (e.g. PA28, C172).
    - hidden (Boolean Column): if it is an official aircraft profile model, it can be hidden from normal users.
    - make_id (String Column): foreign key pointing to the aircraft_make.
    - performance_profile_id (Integer Column): foreign key pointing to the performance_profiles table.
    - make (Relationship): defines the many-to-one relationship with the aircraft_make parent table.
    - aircraft (Relationship): defines the one-to-many relationship with the aircraft child table.
    - performance_profile (Relationship): defines the one-to-one relationship with the performance_profiles parent table.
    """

    __tablename__ = "aircraft_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model = Column(String(255), nullable=False, unique=True)
    code = Column(String(5), nullable=False)
    hidden = Column(Boolean)
    make_id = Column(
        Integer,
        ForeignKey(
            "aircraft_makes.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        )
    )
    performance_profile_id = Column(
        Integer,
        ForeignKey(
            "performance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        )
    )
    make = Relationship("AircraftMake", back_populates="models")
    aircraft = Relationship(
        "Aircraft",
        back_populates="model",
        passive_deletes=True,
        passive_updates=True
    )
    performance_profile = Relationship(
        "PerformanceProfile", back_populates="model")


class PerformanceProfile(BaseModel):
    """
    This class defines the database performance_profiles table.

    Attributes:
    - id (Integer Column): table primary key.
    - center_of_gravity_in (Decimal Column): center of gravity of empty aircraft 
      in inches from datum.
    - empty_weight_lb (Decimal Column): empty weight of the aircraft in lbs.
    - take_off_taxi_fuel_gallons (Decimal Column) = fuel gallons used during start,
      taxi, runup and takeoff.
    - percent_decrease_takeoff_headwind_knot (Decimal Column): percent decrease
    in takeoff distance per knot of headwind.
    - percent_increase_takeoff_tailwind_knot (Decimal Column): percent increase
      in takeoff distance per knot of tailwind.
    - percent_decrease_landing_headwind_knot (Decimal Column): percent decrease
      in landing distance per knot of headwind.
    - percent_increase_landing_tailwind_knot (Decimal Column): percent increase
      in landing distance per knot of tailwind.
    - percent_increase_climb_temperature_c (Integer Column): percent increase in climb
      time, fuel and distance per degree celsius of air temperature above standard.
    - fuel_type_id (Integer Column): foreignkey pointing to the fuel_types table.
    """

    __tablename__ = "performance_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    center_of_gravity_in = Column(DECIMAL(5, 2))
    empty_weight_lb = Column(DECIMAL(7, 2))
    take_off_taxi_fuel_gallons = Column(DECIMAL(3, 1))
    percent_decrease_takeoff_headwind_knot = Column(DECIMAL(4, 2))
    percent_increase_takeoff_tailwind_knot = Column(DECIMAL(4, 2))
    percent_decrease_landing_headwind_knot = Column(DECIMAL(4, 2))
    percent_increase_landing_tailwind_knot = Column(DECIMAL(4, 2))
    percent_increase_climb_temperature_c = Column(DECIMAL(4, 2))
    fuel_type_id = Column(
        Integer,
        ForeignKey(
            "fuel_types.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        )
    )

    aircraft = Relationship(
        "Aircraft",
        back_populates="performance_profile",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    model = Relationship(
        "AircraftModel",
        back_populates="performance_profile",
        uselist=False,
        passive_deletes=True,
        passive_updates=True
    )
    fuel_type = Relationship("FuelType", back_populates="performance_profiles")
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

    Attributes:
    - id (Integer Column): table primary key.
    - registration (String Column): registration or "tail-number"
    - model_id (Integer Column): foreignkey pointing to the aircraft_models table.
    - fuel_type_id (Integer Column): foreignkey pointing to the fuel_types table.
    - owner_id (Integer Column): foreign key that points to the users table.
    - performance_profile_id (Integer Column): foreign key that points to the performance_profiles table.
    """

    __tablename__ = "aircraft"

    id = Column(Integer, primary_key=True, autoincrement=True)
    registration = Column(String(50), nullable=False)

    model_id = Column(
        Integer,
        ForeignKey(
            "aircraft_models.id",
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
        )
    )
    owner_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    model = Relationship("AircraftModel", back_populates="aircraft")
    performance_profile = Relationship(
        "PerformanceProfile", back_populates="aircraft")
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

    Attributes:
    - id (Integer Column): table primary key.
    - percent (String Column): percentage by which to decrease landing/takeoff performance 
    for the runway surface
    - is_takeoff (Boolean Column): true if the pecentage is for takeoff parformance.
    - surface_id (Integer Column): foreign key that links to the runway_surfaces table.
    - performance_profile_id (Integer Column): foreign key that links to the performance_profiles table.
    - surface (Relationship): defines the many-to-one relationship with the runway_surface table.
    - performance_profile (Relationship): defines the many-to-one relationship with the performance_profiles parent table.
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
    This class defines the database weight_balance_profile model.

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): name of the profile.
    - fuel_capacity_gallons (Decimal Column): total fuel capacity.
    - fuel_arm_in (Decimal Column): arm of the fuel wight.
    - max_take_off_weight_lb (Decimal Column): maximum takeoff weight in lbs.
    - max_ramp_weight_lb (Decimal Column): maximum ramp weight in lbs.
    - max_landing_weight_lb (Decimal Column): maximum landing weight in lbs.
    - performance_profile_id (Integer Column): foreign key that links to the performance_profiles table.
    - performance_profile (Relationship): retationship with the performance_profiles parent table.
    - weight_balance_limits (Relationship): list of W&B boundary limits.
    """

    __tablename__ = "weight_balance_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="Normal Category")
    fuel_capacity_gallons = Column(DECIMAL(5, 2), nullable=False)
    fuel_arm_in = Column(DECIMAL(5, 2), nullable=False)
    max_take_off_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    max_ramp_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    max_landing_weight_lb = Column(DECIMAL(7, 2), nullable=False)
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
    baggage_compartments = Relationship(
        "BaggageCompartment",
        back_populates="weight_balance_profile",
        passive_deletes=True,
        passive_updates=True
    )
    seat_rows = Relationship(
        "SeatRow",
        back_populates="weight_balance_profile",
        passive_deletes=True,
        passive_updates=True
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

    Attributes:
    - id (Integer Column): table primary key.
    - from_cg_in (Decimal Column): the cg value of the first point in the W&B limit line in inches.
    - from_weight_lb (Decimal Column): the weight value of the first point in the W&B limit line in lbs.
    - to_cg_in (Decimal Column): the cg value of the last point in the W&B limit line in inches.
    - to_weight_lb (Decimal Column): the weight value of the last point in the W&B limit line in lbs.
    - weight_balance_profile_id (Integer Column): foreign key pointing to the weight_balance_profiles table.
    - weight_balance_profile (Relationship): defines the many_to_one relationship with the 
      weight_balance_profiles parent table.
    """

    __tablename__ = "weight_balance_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_cg_in = Column(DECIMAL(5, 2), nullable=False)
    from_weight_lb = Column(DECIMAL(7, 2), nullable=False, default=0)
    to_cg_in = Column(DECIMAL(5, 2), nullable=False)
    to_weight_lb = Column(DECIMAL(7, 2), nullable=False, default=0)
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

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): the name of the compartment (e.g. compartment 1, back compartment).
    - arm_in (Decimal Column): the W&B arm of the baggage compartment.
    - weight_limit_lb (Decimal Column): the weight limit in lbs, if any.
    - performance_profile_id (Integer Column): foreign key that links to the performance_profiles table.
    - performance_profile (Relationship): defines the many_to_one relationship with the performance_profiles parent table.
    - baggages (Relationship): defines the one_to_many relationship with the baggages table.

    """

    __tablename__ = "baggage_compartments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    arm_in = Column(DECIMAL(5, 2), nullable=False)
    weight_limit_lb = Column(DECIMAL(6, 2))
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
    This class defines the database seat_row model.

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): the name of the row (e.g. pilot seat, back passanger seats)
    - arm_in (Decimal Column): the W&B arm of the row.
    - weight_limit_lb (Decimal Column): the weight limit in lbs, if any.
    - number_of_seats (Integer Column): the number of seats in that row.
    - performance_profile_id (Integer Column): foreign key that links to the performance_profiles table.
    - performance_profile (Relationship): defines the many_to_one relationship with the 
      performance_profiles parent table.
    - passengers (Relationship): defines the one_to_many relationship with the passengers table.
    """

    __tablename__ = "seat_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    arm_in = Column(DECIMAL(5, 2), nullable=False)
    weight_limit_lb = Column(DECIMAL(6, 2))
    number_of_seats = Column(Integer, nullable=False)
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

    Attributes:
    - id (Integer Column): table primary key.
    - weight_lb (Integer Column):
    - pressure_alt_ft (Integer Column): pressure altitude in ft.
    - temperature_c (Integer Column): air temperature at aerodrome, in celsius.
    - groundroll_ft (Integer Column): ground roll distance in ft.
    - obstacle_clearance_ft (Integer Column): distance to clear a 50ft obstacle in ft.
    - performance_profile_id (Integer Column): foreignkey pointing to the performance_profiles parent table.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(7, 2), nullable=False)
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

    Attributes:
    - performance_profile (Relationship): Defines the many-to-one relationship with the 
      performance_profiles parent table.
    """

    __tablename__ = "takeoff_performance_data"

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="takeoff_performance_data"
    )


class LandingPerformance(TakeoffLandingPerformance):
    """
    This class defines the database landing_performance model.

    Attributes:
    - performance_profile (Relationship): Defines the many-to-one relationship with the 
      performance_profiles parent table.
    """

    __tablename__ = "landing_performance_data"

    performance_profile = Relationship(
        "PerformanceProfile",
        back_populates="landing_performance_data"
    )


class ClimbPerformance(BaseModel):
    """
    This class defines the database climb_performance model.

    Attributes:
    - id (Integer Column): table primary key.
    - weight_lb (Decimal Column): the weight limit in lbs, if any.
    - pressure_alt_ft (Integer Column): pressure altitude in ft.
    - temperature_c (Integer Column): air temperature in celsius.
    - time_min (Integer Column): time to climb from sea level, in minutes.
    - fuel_gal (Decimal Column): fuel to climb from sea level, in gallons.
    - distance_nm (Integer Column): distance to climb from sea level, in nautical miles.
    - performance_profile_id (Integer Column): foreignkey pointing to the performance_profiles table.
    - performance_profile (Relationship): Defines the many-to-one relationship with the 
      performance_profiles parent table.
    """

    __tablename__ = "climb_performance_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(7, 2), nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    time_min = Column(Integer, nullable=False)
    fuel_gal = Column(DECIMAL(3, 1), nullable=False)
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
    This class defines the database cruise_performance model.

    Attributes:
    - id (Integer Column): table primary key.
    - weight_lb (Decimal Column): the weight limit in lbs, if any.
    - pressure_alt_ft (Integer Column): pressure altitude in ft.
    - temperature_c (Integer Column): air temperature in celsius.
    - bhp_percent (Integer Column): percentage of engine's BHP, use to cruise.
    - rpm (Integer Column): RPM of the engine during cruise.
    - ktas (Integer Column): true airspeed in knots.
    - gph (Decimal Column): gallons per hour of fuel burned during cruise.
    - performance_profile_id (Integer Column): foreignkey pointing to the performance_profiles parent table.
    - performance_profile (Relationship): Defines the many-to-one relationship with the 
      performance_profiles parent table.
    """

    __tablename__ = "cruise_performance_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(7, 2), nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    bhp_percent = Column(Integer, nullable=False)
    rpm = Column(Integer, nullable=False)
    ktas = Column(Integer, nullable=False)
    gph = Column(DECIMAL(5, 1), nullable=False)
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
    This class defines the database fuel_type model.

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): the name of the fuel (e.g. kerosene, 100LL).
    - density_lb_gal (Decimal Column): density of the fuel in lbs per gallon.
    - performance_profile (Relationship): Defines the one_to_many relationship with the 
      performance_profiles child table.
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
