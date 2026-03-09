"""
Router principal que agrupa todos los endpoints.
"""

from fastapi import APIRouter

from src.api import admin, admin_ws, auth, health, webhook

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(webhook.router, tags=["Webhook"])
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(admin_ws.router)
