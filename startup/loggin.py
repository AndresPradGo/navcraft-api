"""
Logger config module

This module configures the logger.

Usage: 
- Import the config_logger function into the main.py module and call it. 

"""
import logging


def config_logger():
    """
    This function fonfigures the logger.
    """
    logging.basicConfig(filename='errors.log', level=logging.CRITICAL)
