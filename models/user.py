"""
Sqlalchemy user model

This module defines the user related db-table models.

Usage: 
- Import the required model class to create db-tables and db-table entries.

"""

from sqlalchemy import Column, Integer, DECIMAL, String
from sqlalchemy.orm import Relationship

from models.base import BaseModel


class PassengerProfile(BaseModel):
    """
    This class defines the database passenger_profile model.

    Attributes:
    - id (Integer Column): table primary key.
    - name (String Column): passenger name.
    - weight_lb (Decimal Column): passenger weight in lbs.
    - passengers (Relationship): defines the one-to-many relationship with the passenger table.
    """

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    weight_lb = Column(DECIMAL(4, 1), nullable=False, default=200.0)

    passengers = Relationship(
        "Passenger",
        back_populates="profile",
        passive_deletes=True,
        passive_updates=True
    )
