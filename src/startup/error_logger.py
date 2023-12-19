"""
Error Logger Startup Module

Module initiates the error logger with sentry.io.

Usage: 
- Import the init_logger function and call it before initiating the FastAPI app.

"""

import sentry_sdk


def init_logger():
    """
    This function initiates the error logger.
    """
    sentry_sdk.init(
        dsn="https://ab69a96a2792e940845e18c17bf637ee@o1258167.ingest.sentry.io/4506419141410816",
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
