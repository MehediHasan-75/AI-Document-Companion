"""
Routes Index Module
-------------------

Aggregates all route modules in the routes/ folder.
"""

from fastapi import APIRouter
from . import file_routes
from . import query_routes
# Create a central router
router = APIRouter()

# Include all routers
router.include_router(file_routes.router)
# router.include_router(query_routes.router, prefix="/api")
# Future routers can be added here:
# from . import user_routes
# router.include_router(user_routes.router)