"""
Sqlalchemy user model

This module defines the user related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from jose import jwt
from sqlalchemy import Column, Integer, DECIMAL, String, Boolean, ForeignKey
from sqlalchemy.orm import Relationship

from models.base import BaseModel
from utils import environ_variable_tools as environ


class User(BaseModel):
    """
    This class defines the database users table.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    weight_lb = Column(DECIMAL(4, 1), nullable=False, default=200.0)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
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
    user_waypoints = Relationship(
        "UserWaypoint",
        back_populates="creator",
        passive_deletes=True,
        passive_updates=True
    )
    vfr_waypoints = Relationship(
        "VfrWaypoint",
        back_populates="creator",
        passive_deletes=True,
        passive_updates=True
    )
    persons_on_board = Relationship(
        "PersonOnBoard",
        back_populates="user",
        passive_deletes=True,
        passive_updates=True
    )

    def generate_auth_token(self):
        """
        This method generates a Jason Web Token.

        Parameters:
        - expires_delta (timedelta): An optional timedelta specifying the expiration time of the JWT.

        Returns: 
        - str: Jason Web Token.
        """
        jwt_key = environ.get("jwt_secret_key")
        jwt_algorithm = environ.get("jwt_algorithm")

        permissions = ["admin", "master"] if self.is_admin and self.is_master else [
            "admin"] if self.is_admin else []
        to_encode = {"email": self.email,
                     "permissions": permissions, "active": self.is_active}

        encoded_jwt = jwt.encode(to_encode, jwt_key, algorithm=jwt_algorithm)

        return encoded_jwt


class PassengerProfile(BaseModel):
    """
    This class defines the database passenger_profiles table.
    """

    __tablename__ = "passenger_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    weight_lb = Column(DECIMAL(5, 2), nullable=False, default=200.0)
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
    persons_on_board = Relationship(
        "PersonOnBoard",
        back_populates="passenger_profile",
        passive_deletes=True,
        passive_updates=True
    )
