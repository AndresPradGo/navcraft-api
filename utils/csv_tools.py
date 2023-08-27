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


def from_list(data: List[Dict[str, Any]]):
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


def to_list(file_name: str) -> List[Dict[str, Any]]:
    """
    This function reads a csv file and coverts it to a list of dictionary data.

    Parameters:
    - file_name (str): the plain file name, without path or file type.

    Returns: 
    - List[Dict[str, Any]]: list of dictionaries with data.
    """

    file_path = f"{_PATH}{file_name}.csv"
    data_list = []

    with open(file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            data_list.append(row)

    return data_list
