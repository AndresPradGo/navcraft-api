"""
CSV File Tools

This module creates a function get data from and to csv files.

Usage: 
- Import the function you need.

"""

import csv
import io
from typing import List, Dict, Any

from fastapi import UploadFile, HTTPException, status
from pydantic import ValidationError

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


def check_format(file: UploadFile) -> None:
    """
    This function check the file is a .csv file, and raises an 
    HTTPException if not.

    Parameters:
    - file(fastapi UploadFile): csv file in memore.

    Returns: None
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files allowed",
        )


async def extract_schemas(file: UploadFile, schema):
    """
    This function will extract the data from the csv-file,
    and return it as a list of schema objects.

    Parameters:
    - file(fastapi UploadFile): csv file in memore.
    - schema (pydantic model): the schema to chape the data.

    Returns: 
    - list: list of schema objects with the data in the csv file.

    Raise:
    HTTPException (400): If the data in the file is not in the correct format
    """
    content = await file.read()
    decoded_content = content.decode("utf-8")

    # Check data is in the correct format
    data_list = []
    try:
        data_list = [schema(
            **w) for w in utf8_to_list(utf8_content=decoded_content)]
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.errors()
        )

    return data_list
