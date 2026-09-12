"""Compatibility entry point for ``uvicorn app:app``; implementation lives in web.app."""

from web.app import app

__all__ = ["app"]
