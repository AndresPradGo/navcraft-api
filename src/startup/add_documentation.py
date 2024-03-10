"""
Documentation startup module

Module asigns adds the /docs route to the API, to display the APIS's documentation.

Usage: 
- Import the add_documentation function, and pass the FastAPI app as a parameter.

"""

from fastapi import FastAPI, status, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


def add_documentation(app: FastAPI):
    """
    This function adds the API /docs route
    """
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/docs", include_in_schema=False)
    def overridden_swagger(req: Request) -> HTMLResponse:
        root_path = req.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + app.openapi_url
        oauth2_redirect_url = app.swagger_ui_oauth2_redirect_url
        if oauth2_redirect_url:
            oauth2_redirect_url = root_path + oauth2_redirect_url
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=app.title + " | Docs",
            oauth2_redirect_url=oauth2_redirect_url,
            init_oauth=app.swagger_ui_init_oauth,
            swagger_favicon_url="/static/logo.png",
            swagger_ui_parameters=app.swagger_ui_parameters,
        )

    @app.get("/redoc", include_in_schema=False)
    def overridden_redoc():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not Found"
        )
