"""Route aggregation for all API modules."""

from fastapi import APIRouter

from . import auth_routes, conversation_routes, file_routes, process_routes, query_routes

router = APIRouter()

router.include_router(auth_routes.router)
router.include_router(file_routes.router)
router.include_router(process_routes.router)
router.include_router(query_routes.router)
router.include_router(conversation_routes.router)
