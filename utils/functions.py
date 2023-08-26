"""
Useful Reusable Functions

Usage: 
- Import the required function and call it.
"""


def clean_string(input_string: str) -> str:
    '''
    This functions takes a string and clens it by:
    - Removing leading and trailing white spaces.
    - Converts to lowercase and capitalizes first letter.
    - Replaces consecutive white spaces with a single space.

    Parameters:
    - input_string (str): string to be cleaned.

    Returns:
    str: cleaned string.
    '''

    return ' '.join([word.capitalize() for word in input_string.strip().split()])
