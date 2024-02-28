"""
Error Logger Startup Module

Module initiates the error logger with sentry.io.

Usage: 
- Import the init_logger function and call it before initiating the FastAPI app.

"""

import sentry_sdk
from utils import environ_variable_tools as environ


def init_logger():
    """
    This function initiates the error logger.
    """
    sentry_dsn = environ.get("sentry_dsn")
    if sentry_dsn is not None and sentry_dsn != "":
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
