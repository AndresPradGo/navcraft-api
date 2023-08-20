"""
Sqlalchemy aircraft model

This module defines the aircraft related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, Float, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class AircraftModel(BaseModel):
    """
    This class defines the database aircraft_model model.

    Attributes:
    - id (Integer Column): table primary key.
    - make (String Column): aircraft make.
    - model (String Column): aircraft model.
    - series (String Column): aircraft series.
    code (String Column): short code that identifies the aircraft (e.g. PA28-161, C172R)
    - aircraft (Relationship): defines the one-to-many relationship with the aircraft table.
    """

    __tablename__ = "aircraft_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    series = Column(String(50))
    code = Column(String(50), nullable=False, unique=True)

    aircraft = Relationship(
        "Aircraft",
        back_populates="model",
        passive_deletes=True,
        passive_updates=True
    )


class Aircraft(BaseModel):
    """
    This class defines the database aircraft model.

    Attributes:
    - id (Integer Column): table primary key.
    - registration (String Column):
    - is_model (Boolean Column): true if the aircraft profile is a general model.
    - center_of_gravity_in (Decimal Column): center of gravity of empty aircraft 
      in inches from datum.
    - empty_weight_lb (Decimal Column): empty weight of the aircraft in lbs.
    - fuel_capacity_gallons (Decimal Column): total fuel capacity.
    - fuel_arm_in (Decimal Column): arm of the fuel wight.
    - max_take_off_weight_lb (Decimal Column): maximum takeoff weight in lbs.
    - max_ramp_weight_lb (Decimal Column): maximum ramp weight in lbs.
    - max_landing_weight_lb (Decimal Column): maximum landing weight in lbs.
    - percent_decrease_takeoff_headwind_knot (Float Column): percent decrease
      in takeoff distance per knot of headwind.
    - percent_increase_takeoff_tailwind_knot (Float Column): percent increase
      in takeoff distance per knot of tailwind.
    - percent_decrease_landing_headwind_knot (Float Column): percent decrease
      in landing distance per knot of headwind.
    - percent_increase_landing_tailwind_knot (Float Column): percent increase
      in landing distance per knot of tailwind.
    - percent_increase_climb_temperature_c (Integer Column): percent increase in climb
      time, fuel and distance per degree celsius of air temperature above standard.
    - model_id (Integer Column): foreignkey pointing to the aircraft_models table.
    - fuel_type_id (Integer Column): foreignkey pointing to the fuel_types table.
    - owner_id (Integer Column): foreign key that points to the users table.
    - model (Relationship): defines the many-to-one relationship with the aircraft_models table.
    - flights (Relationship): list of flights with this particular aircraft.
    - performance_decreace_runway_surfaces_percent (Relationship): list of percentages by which 
      to decrease landing/takeoff performance for different runway surfaces.
    - weight_balance_profiles (Relationship): list of W&B profiles for different categories.
    - baggage_compartments (Relationship): list of baggage compartments the aircraft is equipt with.
    - seat_rows (Relationship): list of seat rows the aircraft is equipt with.
    - takeoff_performance_data (Relationship): takeoff performance data table.
    - landing_performance_data (Relationship): landing performance data table.
    - climb_performance_data (Relationship): climb performance data table.
    - cruise_performance_data (Relationship): cruise performance data table.
    - fuel_type (Relationship): Defines the many-to-one relationship with the fuel_types table.
    - owner (Relationship): defines the many-to-one relationship with the users table.
    - compass_card_data (Relationship): compass card data table.
    - airspeed_calibration_data (Relationship): airspeed calibration data table.
    """

    __tablename__ = "aircraft"

    id = Column(Integer, primary_key=True, autoincrement=True)
    registration = Column(String(10), nullable=False, default="Model")
    is_model = Column(Boolean, nullable=False, default=False)
    center_of_gravity_in = Column(DECIMAL(5, 2), nullable=False, default=0)
    empty_weight_lb = Column(DECIMAL(7, 2), nullable=False, default=0)
    fuel_capacity_gallons = Column(DECIMAL(5, 2), nullable=False)
    fuel_arm_in = Column(DECIMAL(5, 2), nullable=False)
    max_take_off_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    max_ramp_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    max_landing_weight_lb = Column(DECIMAL(7, 2), nullable=False)
    percent_decrease_takeoff_headwind_knot = Column(
        Float,
        nullable=False,
        default=0
    )
    percent_increase_takeoff_tailwind_knot = Column(
        Float,
        nullable=False,
        default=0
    )
    percent_decrease_landing_headwind_knot = Column(
        Float,
        nullable=False,
        default=0
    )
    percent_increase_landing_tailwind_knot = Column(
        Float,
        nullable=False,
        default=0
    )
    percent_increase_climb_temperature_c = Column(
        Float,
        nullable=False,
        default=0
    )
    model_id = Column(
        Integer,
        ForeignKey(
            "aircraft_models.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    fuel_type_id = Column(
        Integer,
        ForeignKey(
            "fuel_types.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        nullable=False
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
    flights = Relationship(
        "Flight",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    performance_decreace_runway_surfaces_percent = Relationship(
        "SurfacePerformanceDecrease",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    weight_balance_profiles = Relationship(
        "WeightBalanceProfile",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    baggage_compartments = Relationship(
        "BaggageCompartment",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    seat_rows = Relationship(
        "SeatRow",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    takeoff_performance_data = Relationship(
        "TakeoffPerformance",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    landing_performance_data = Relationship(
        "LandingPerformance",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    climb_performance_data = Relationship(
        "ClimbPerformance",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    cruise_performance_data = Relationship(
        "CruisePerformance",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    fuel_type = Relationship(
        "FuelType",
        back_populates="aircraft"
    )
    owner = Relationship("User", back_populates="aircraft")
    compass_card_data = Relationship(
        "CompassCard",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
    airspeed_calibration_data = Relationship(
        "AirspeedCalibration",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )

    class SurfacePerformanceDecrease(BaseModel):
        """
        This class defines the database surface_performance_decrease model.

        Attributes:
        - id (Integer Column): table primary key.
        - percent (String Column): percentage by which to decrease landing/takeoff performance 
        for the runway surface
        - is_takeoff (Boolean Column): true if the pecentage is for takeoff parformance.
        - surface_id (Integer Column): foreign key that links to the runway_surfaces table.
        - aircraft_id (Integer Column): foreign key that links to the aircraft table.
        - surface (Relationship): defines the many-to-one relationship with the runway_surface table.
        - aircraft (Relationship): defines the many-to-one relationship with the aicraft table.
        """

        __tablename__ = "surfaces_performance_decrease"

        id = Column(Integer, primary_key=True, autoincrement=True)
        percent = Column(Float, nullable=False, default=0)
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
        aircraft_id = Column(
            Integer,
            ForeignKey(
                "aircraft.id",
                ondelete="CASCADE",
                onupdate="CASCADE"
            ),
            nullable=False
        )

        surface = Relationship(
            "RunwaySurface", back_populates="aircraft_performance_percentages")
        aircraft = Relationship(
            "Aircraft",
            back_populates="performance_decreace_runway_surfaces_percent"
        )


class AircraftCategory(BaseModel):
    """
    This class defines the database aircraft_category model.

    Attributes:
    - id (Integer Column): table primary key.
    - category (String Column): aircraft category.
    - weight_balance_profiles (Relationship): list of W&B profiles with this category.
    """

    __tablename__ = "aircraft_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(10), nullable=False, unique=True)

    weight_balance_profiles = Relationship(
        "WeightBalanceProfile",
        back_populates="category",
        passive_deletes=True,
        passive_updates=True
    )


class WeightBalanceProfile(BaseModel):
    """
    This class defines the database weight_balance_profile model.

    Attributes:
    - id (Integer Column): table primary key.
    - category_id (Integer Column): foreign key representing the id in the aircraft_categories table.
    - aircraft_id (Integer Column): foreign key that links to the aircraft table.
    - category (Relationship): defines the many_to_one relationship with the aircraft_categories table.
    - aircraft (Relationship): the aircraft for which the W&B profile is for.
    - weight_balance_limits (Relationship): list of W&B boundary limits.
    """

    __tablename__ = "weight_balance_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(
        Integer,
        ForeignKey(
            "aircraft_categories.id",
            ondelete="RESTRICT",
            onupdate="CASCADE"
        ),
        nullable=False
    )
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    category = Relationship(
        "AircraftCategory",
        back_populates="weight_balance_profiles"
    )
    aircraft = Relationship(
        "Aircraft",
        back_populates="weight_balance_profiles"
    )
    weight_balance_limits = Relationship(
        "WeightBalanceLimit",
        back_populates="profile",
        passive_deletes=True,
        passive_updates=True
    )


class WeightBalanceLimit(BaseModel):
    """
    This class defines the database weight_balance_limit model.

    Attributes:
    - id (Integer Column): table primary key.
    - from_cg_in (Decimal Column): the cg value of the first point in the W&B limit line in inches.
    - from_weight_lb (Decimal Column): the weight value of the first point in the W&B limit line in lbs.
    - to_cg_in (Decimal Column): the cg value of the last point in the W&B limit line in inches.
    - to_weight_lb (Decimal Column): the weight value of the last point in the W&B limit line in lbs.
    - profile_id (Integer Column): foreign key pointing to the weight_balance_profiles table.
    - profile (Relationship): defines the many_to_one relationship with the weight_balance_profiles table.
    """

    __tablename__ = "weight_balance_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_cg_in = Column(DECIMAL(5, 2), nullable=False)
    from_weight_lb = Column(DECIMAL(7, 2), nullable=False, default=0)
    to_cg_in = Column(DECIMAL(5, 2), nullable=False)
    to_weight_lb = Column(DECIMAL(7, 2), nullable=False, default=0)
    profile_id = Column(
        Integer,
        ForeignKey(
            "weight_balance_profiles.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    profile = Relationship(
        "WeightBalanceProfile",
        back_populates="weight_balance_limits"
    )


class BaggageCompartment(BaseModel):
    """
    This class defines the database baggage_compartment model.

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): the name of the compartment (e.g. compartment 1, back compartment).
    - arm_in (Decimal Column): the W&B arm of the baggage compartment.
    - weight_limit_lb (Decimal Column): the weight limit in lbs, if any.
    - aircraft_id (Integer Column): foreign key that links to the aircraft table.
    - aircraft (Relationship): defines the many_to_one relationship with the aircraft table.
    - baggages (Relationship): defines the one_to_many relationship with the baggages table.

    """

    __tablename__ = "baggage_compartments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    arm_in = Column(DECIMAL(5, 2), nullable=False)
    weight_limit_lb = Column(DECIMAL(6, 2))
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aircraft = Relationship(
        "Aircraft",
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
    - aircraft_id (Integer Column): foreign key that links to the aircraft table.
    - aircraft (Relationship): defines the many_to_one relationship with the aircraft table.
    - passengers (Relationship): defines the one_to_many relationship with the passengers table.
    """

    __tablename__ = "seat_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    arm_in = Column(DECIMAL(5, 2), nullable=False)
    weight_limit_lb = Column(DECIMAL(6, 2))
    number_of_seats = Column(Integer, nullable=False)
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aircraft = Relationship(
        "Aircraft",
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
    - aircraft_id (Integer Column): foreignkey pointing to the aircraft table.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(7, 2), nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    groundroll_ft = Column(Integer, nullable=False)
    obstacle_clearance_ft = Column(Integer, nullable=False)
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )


class TakeoffPerformance(TakeoffLandingPerformance):
    """
    This class defines the database takeoff_performance model.

    Attributes:
    - aircraft (Relationship): Defines the many-to-one relationship with the aircraft table.
    """

    __tablename__ = "takeoff_performance_data"

    aircraft = Relationship(
        "Aircraft",
        back_populates="takeoff_performance_data"
    )


class LandingPerformance(TakeoffLandingPerformance):
    """
    This class defines the database landing_performance model.

    Attributes:
    - aircraft (Relationship): Defines the many-to-one relationship with the aircraft table.
    """

    __tablename__ = "landing_performance_data"

    aircraft = Relationship(
        "Aircraft",
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
    - aircraft_id (Integer Column): foreignkey pointing to the aircraft table.
    - aircraft (Relationship): Defines the many-to-one relationship with the aircraft table.
    """

    __tablename__ = "climb_performance_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(7, 2), nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    time_min = Column(Integer, nullable=False)
    fuel_gal = Column(DECIMAL(3, 1), nullable=False)
    distance_nm = Column(Integer, nullable=False)
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aircraft = Relationship(
        "Aircraft",
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
    - aircraft_id (Integer Column): foreignkey pointing to the aircraft table.
    - aircraft (Relationship): Defines the many-to-one relationship with the aircraft table.
    """

    __tablename__ = "cruise_performance_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weight_lb = Column(DECIMAL(7, 2), nullable=False)
    pressure_alt_ft = Column(Integer, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    bhp_percent = Column(Integer, nullable=False)
    rpm = Column(Integer, nullable=False)
    ktas = Column(Integer, nullable=False)
    gph = Column(DECIMAL(3, 1), nullable=False)
    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aircraft = Relationship(
        "Aircraft",
        back_populates="cruise_performance_data"
    )

    class FuelType(BaseModel):
        """
        This class defines the database fuel_type model.

        Attributes:
        - id (Integer Column): table primary key.
        - name (String Column): the name of the fuel (e.g. kerosene, 100LL).
        - density_lb_gal (Decimal Column): density of the fuel in lbs per gallon.
        - aircraft (Relationship): Defines the one_to_many relationship with the aircraft table.
        """

        __tablename__ = "fuel_types"

        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(50), nullable=False, unique=True)
        density_lb_gal = Column(DECIMAL(4, 2), nullable=False)

        aircraft = Relationship(
            "Aircraft",
            back_populates="fuel_type",
            passive_deletes=True,
            passive_updates=True
        )


class CompassCard(BaseModel):
    """
    This class defines the database compass_card model.

    Attributes:
    - id (Integer Column): table primary key.
    - uncorrected (Integer Column): the compass track before correction. The track you want to steer.
    - corrected (Integer Column): the compass track after correction. The track you have to steer.
    - aircraft_id (Integer Column): foreignkey pointing to the aircraft table.
    - aircraft (Relationship): Defines the many-to-one relationship with the aircraft table.
    """

    __tablename__ = "compass_card_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uncorrected = Column(Integer, nullable=False)
    corrected = Column(Integer, nullable=False)

    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aircraft = Relationship(
        "Aircraft",
        back_populates="compass_card_data"
    )


class AirspeedCalibration(BaseModel):
    """
    This class defines the database airspeed_calibration model.

    Attributes:
    - id (Integer Column): table primary key.
    - kias (Integer Column): indicated airspeed in knots.
    - kcas (Integer Column): calibrated airspeed in knots.
    - aircraft_id (Integer Column): foreignkey pointing to the aircraft table.
    - aircraft (Relationship): Defines the many-to-one relationship with the aircraft table.
    """

    __tablename__ = "airspeed_calibration_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kias = Column(Integer, nullable=False)
    kcas = Column(Integer, nullable=False)

    aircraft_id = Column(
        Integer,
        ForeignKey(
            "aircraft.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    aircraft = Relationship(
        "Aircraft",
        back_populates="airspeed_calibration_data"
    )
