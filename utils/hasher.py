"""
Passlib and bcrypt tools

This module creates a class that handles hashing and verifying passwords.

Usage: 
- Import the Hasher class and use the bycript or verify methods.

"""

from passlib.context import CryptContext


class Hasher():
    """
    This class defines the mehtods to hash and verify passwords.

    Attributes: 
    - crypt_context: instance of CryptContext used to hash passwords.

    Methods:
    - bcrypt(password: "str"): hashes the password using bcrypt and returns it.
    - verify(plain_pass: "str", hashed_pass: "str"): compares the hashed_pass with 
        plain_pass and returns True if equal. 
    """

    crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    def bcrypt(cls, password: str):
        """
        This method hashes the password using bcrypt and returns it.

        Parameters:
        - password (str): unhashed password

        Returns: 
        - str: hashed passwrod.
        """
        return cls.crypt_context.hash(password)

    @classmethod
    def verify(cls, plain_pass: str, hashed_pass: str):
        """
        This method ompares the hashed_pass with plain_pass and returns True if equal. 

        Parameters:
        - plain_pass (str): unhashed password.
        - hashed_pass (str): hashed password.

        Returns: 
        - str: hashed passwrod.
        """
        return cls.crypt_context.verify(plain_pass, hashed_pass)
