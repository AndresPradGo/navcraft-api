"""
CSV File Tools

This module creates a function get data from and to csv files.

Usage: 
- Import the function you need.

"""

import csv
import io
from typing import List, Dict, Any

_PATH = "static_data/"


def list_to_buffer(data: List[Dict[str, Any]]):
    """
    This function writes a list of dictionary data into a csv file.

    Parameters:
    - data (List[Dict[str, Any]]): list of data to write into csv file

    Returns: 
    - Any: file buffer.
    """

    column_headers = list(data[0].keys())

    output = io.StringIO()
    csv_writer = csv.DictWriter(output, fieldnames=column_headers)
    csv_writer.writeheader()
    csv_writer.writerows(data)

    return output


def utf8_to_list(utf8_content: str) -> List[Dict[str, Any]]:
    """
    This function reads a csv file and coverts it to a list of dictionary data.

    Parameters:
    - file_name (str): the plain file name, without path or file type.

    Returns: 
    - List[Dict[str, Any]]: list of dictionaries with data.
    """

    data_list = []

    csv_reader = csv.DictReader(io.StringIO(utf8_content))
    for row in csv_reader:
        data_list.append(row)

    return data_list
