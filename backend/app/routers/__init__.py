"""Роутеры приложения."""

from .auth import router as auth_router
from .sessions import router as sessions_router

__all__ = ["auth_router", "sessions_router"]