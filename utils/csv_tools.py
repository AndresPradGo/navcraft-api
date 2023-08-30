"""
CSV File Tools

This module creates a function get data from and to csv files.

Usage: 
- Import the function you need.

"""

import csv
import io
from typing import List, Dict, Any
import zipfile

from fastapi import UploadFile, HTTPException, status
from pydantic import ValidationError


def csv_to_list(file_path: str) -> List[Dict[str, Any]]:
    """
    This function reads a csv-file and returns the data in a list of dictionaries.

    Parameters:
    - file_path (str): csv-file path.

    Returns: 
    - list: list of data.
    """

    data_list = []
    with open(file_path, mode="r", newline="", encoding="utf-8") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            data_list.append(row)

    return data_list


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


def pre_process_aerodrome_data(runway_list: List[Dict[str, Any]]):
    """
    This function preprocess the aerodrome data.

    Parameters:
    - runway_list(list): preprocessed aerodrome list.

    Returns: processed aerodrome list
    """
    return [{**a, "status": a["status_id"]} for a in runway_list]


def pre_process_runway_data(runway_list: List[Dict[str, Any]]):
    """
    This function loops through a list of Runway data dictionaries, 
    and removes the 'position' if it is an empty string

    Parameters:
    - runway_list(list): preprocessed tunway list.

    Returns: processed runway list
    """
    return [{
        "aerodrome_id": r["aerodrome_id"],
        "number": r["number"],
        "length_ft": r["length_ft"],
        "surface_id": r["surface_id"]
    } if r["position"] == "" else {
        "aerodrome_id": r["aerodrome_id"],
        "number": r["number"],
        "position": r["position"],
        "length_ft": r["length_ft"],
        "surface_id": r["surface_id"]
    } for r in runway_list]


async def extract_schemas(file: UploadFile, schema, is_runway: bool = False, is_aerodrome: bool = False):
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
    dict_list = utf8_to_list(utf8_content=content.decode("utf-8"))

    if is_runway:
        dict_list = pre_process_runway_data(dict_list)
    elif is_aerodrome:
        dict_list = pre_process_aerodrome_data(dict_list)

    data_list = []
    try:
        data_list = [schema(
            **i) for i in dict_list]
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.errors()
        )

    return data_list


def zip_csv_files_from_data_list(csv_files_data: List[Dict[str, Any]]):
    """
    This function will extract the data from a list of data,
    and return it as a zip of csv-files.

    Parameters:
    - csv_files_data(list[dict]): list of dictionaries with the data.

    Returns: 
    - Any: file buffer.
    """

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for csv_file_data in csv_files_data:
            csv_content = list_to_buffer(csv_file_data["data"])
            zipf.writestr(csv_file_data["name"], csv_content.getvalue())

    zip_buffer.seek(0)

    return zip_buffer
