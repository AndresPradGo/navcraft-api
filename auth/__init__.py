"""
Auth package init file

This init module imports all the auth functions,
so they can be imported externaly. 

Usage: 
- This module will run automatically, whenever the models package gets imported.

"""
from auth.functions import validate_user, validate_admin_user, validate_master_user
from auth.hasher import Hasher
