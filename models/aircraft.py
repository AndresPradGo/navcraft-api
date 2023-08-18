"""
Sqlalchemy aircraft model

This module defines the aircraft related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, Float, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class AicraftModel(BaseModel):
    """
    This class defines the database aircraft_model model.

    Attributes:
    - id (Integer Column): table primary key.
    - make (String Column): aircraft make.
    - model (String Column): aircraft model.
    - series (String Column): aircraft series.
    - aircraft (Relationship): defines the one-to-many relationship with the aircraft table.
    """

    __tablename__ = "aircraft_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    series = Column(String(50))

    aircraft = Relationship(
        "Aircraft",
        back_populates="model",
        passive_deletes=True,
        passive_updates=True
    )


class Aircraft(BaseModel):
    """
    This class defines the database aircraft_model model.

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
    - model (Relationship): defines the many-to-one relationship with the aircraft_models table.
    - flights (Relationship): list of flights with this particular aircraft.
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

    model = Relationship("AircraftModel", back_populates="aircraft")
    flights = Relationship(
        "Flight",
        back_populates="aircraft",
        passive_deletes=True,
        passive_updates=True
    )
