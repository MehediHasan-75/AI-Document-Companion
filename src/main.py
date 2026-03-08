"""
Main Application Entry Point
----------------------------

Initializes FastAPI app and mounts all routes from routes/index.py
"""

from fastapi import FastAPI
from src.routes import index 

app = FastAPI(
    title="AI Document Companion API",
    version="1.0.0",
    description="API for managing files"
)

# Mount all routes from routes/index.py
app.include_router(index.router)

# Root endpoint
@app.get("/", summary="API Root")
async def root():
    return {"message": "AI Document Companion API is running"}