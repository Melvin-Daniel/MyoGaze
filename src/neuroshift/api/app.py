"""ASGI entry: uvicorn src.neuroshift.api.app:app"""

from . import create_app

app = create_app()
