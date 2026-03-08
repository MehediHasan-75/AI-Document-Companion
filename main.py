"""
Top‑level ASGI entrypoint for Uvicorn.

This file simply re‑exports the FastAPI ``app`` defined in ``src.main`` so
you can run the server with:

    uvicorn main:app --reload
"""
from src.main import app  # noqa: F401

