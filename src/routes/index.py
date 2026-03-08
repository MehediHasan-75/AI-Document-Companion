"""
Routes Index Module
-------------------

Aggregates all route modules in the routes/ folder.
"""

from fastapi import APIRouter

from . import file_routes, process_routes, query_routes

router = APIRouter()

router.include_router(file_routes.router)
router.include_router(process_routes.router)
router.include_router(query_routes.router)

# Future routers can be added here, e.g.:
# from . import user_routes
# router.include_router(user_routes.router)