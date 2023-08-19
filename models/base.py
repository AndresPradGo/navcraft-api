"""
Sqlalchemy base model

This module defines the BaseModel, from which all the database models will inherit.

Usage: 
- Import the Model class from this module, when creating the db tables.
- import the BaseModel class from this module, when defining a new db-table model.

"""

from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

from utils.db import session

Model = declarative_base()
Model.query = session.query_property()


class BaseModel(Model):
    """
    This class defines the database base model, 
    which will be the parent for all the db-table models.

    Attributes:
    - created_at (DateTime Column): date-time at which the table row entry was created.
    - last_updated (DateTime Column): date-time at which the table row entry was last updated.
    """

    __abstract__ = True

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())
    last_updated = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow(),
        onupdate=datetime.utcnow()
    )