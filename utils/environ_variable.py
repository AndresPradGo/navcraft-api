"""
Environment Variables Getter Tools

This module creates a function to get the environment variables for this project,
which names are listed in the config directory.

Usage: 
- Import the get function to get environment variables.

"""

import json
from os import environ


def get(var_key: str):
    """
    This method gets the value of the environment variable and returns it.

    Parameters:
    - var_key (str): key to get the name of the environme variable, 
      from the config directory.

    Returns: 
    - str: value of the environment variable.
    """

    with open("config/environment_variables.json", "r") as json_file:
        var_names = json.load(json_file)

    return environ.get(var_names[var_key])
