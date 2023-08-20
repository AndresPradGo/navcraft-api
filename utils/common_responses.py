"""
Common Server Response Messages

This module defines common and general response messages.

Usage: 
- Import the function returning the response you want to use, and call it.

"""

import re


def internal_server_error() -> str:
    """
    This function returns an internal server error message.

    Parameters: None

    Returns: 
    str: internal server error general message.
    """
    message = '''
        An unexpected server error occurred. Our team has been 
        notified and is investigating the issue. We apologize 
        for any inconvenience.
    '''
    return re.sub(r'\s+', ' ', message).strip()
