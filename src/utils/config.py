
"""
Functions to get configuration variables form the config directory.

Usage: 
- Import the required function and call it.
"""

import json

_PATH = "config/"


def get_table_header(table_name: str):
    """
    Gets the table headers for csv downloadable files.

    Parameters:
    - table_name (str): name of the table.

    Returns: 
    - dict: dictionary with table headers.
    """
    with open(f"{_PATH}csv_headers.json", mode="r", encoding="utf-8") as json_file:
        tables = json.load(json_file)

    return tables[table_name]


def get_constant(name: str) -> float:
    """
    Gets the physics constants form config directory.

    Parameters:
    - name (str): name of the constant.

    Returns: 
    - Float: constant value.
    """
    with open(f"{_PATH}physics_constants.json", mode="r", encoding="utf-8") as json_file:
        constants = json.load(json_file)

    return constants[name]
