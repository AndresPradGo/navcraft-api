"""
Models package init file

This init module imports all the models from the models package,
so they can be imported externaly. 

Usage: 
- This module will run automatically, whenever the models package gets imported.

"""

from models.base import Model
from models.aircraft import *
from models.flight import *
from models.user import *
from models.waypoint import *
from models.weather import *
