"""
Router principal que agrupa todos los endpoints.
"""

from fastapi import APIRouter

from src.api import health, webhook

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(webhook.router, tags=["Webhook"])
