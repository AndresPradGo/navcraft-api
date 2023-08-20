"""
Sqlalchemy user model

This module defines the user related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class User(BaseModel):
    """
    This class defines the database user model.

    Attributes:
    - id (Integer Column): table primary key.
    - email (String Column): user email.
    - name (String Column): user name.
    - password (String Column): user password.
    - weight_lb (Decimal Column): user weight in lbs.
    - is_admin (Boolean Column): true if the user is admin. Admin users have privileges 
      like adding aerodromes and aircraft base models.
    - is_master (Boolean Column): true if the user is master. Only master users can add 
      new admin users. Master users have to be Admin Users.
      aircraft (Relationship): defines the one-to-many relationship with the aircraft table.
      flights (Relationship): defines the one-to-many relationship with the flights table.
    - passenger_profiles (Relationship): defines the one-to-many relationship with the 
      passenger_profile table.
    - waypoints (Relationship): defines the one-to-many relationship with the waypoints table.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    weight_lb = Column(DECIMAL(4, 1), nullable=False, default=200.0)
    password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_master = Column(Boolean, nullable=False, default=False)

    aircraft = Relationship(
        "Aircraft",
        back_populates="owner",
        passive_deletes=True,
        passive_updates=True
    )
    flights = Relationship(
        "Flight",
        back_populates="pilot",
        passive_deletes=True,
        passive_updates=True
    )
    passenger_profiles = Relationship(
        "PassengerProfile",
        back_populates="creator",
        passive_deletes=True,
        passive_updates=True
    )
    waypoints = Relationship(
        "Waypoint",
        back_populates="creator",
        passive_deletes=True,
        passive_updates=True
    )


class PassengerProfile(BaseModel):
    """
    This class defines the database passenger_profile model.

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): passenger name.
    - weight_lb (Decimal Column): passenger weight in lbs.
    - creator_id (Integer Column): foreign key that points to the users table.
    - creator (Relationship): defines the many-to-one relationship with the users table.
    - passengers (Relationship): defines the one-to-many relationship with the passenger table.
    """

    __tablename__ = "passenger_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    weight_lb = Column(DECIMAL(4, 1), nullable=False, default=200.0)
    creator_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    creator = Relationship("User", back_populates="passenger_profiles")
    passengers = Relationship(
        "Passenger",
        back_populates="profile",
        passive_deletes=True,
        passive_updates=True
    )
