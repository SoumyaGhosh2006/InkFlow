"""
InkFlow FastAPI Dependency Injection Module.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module exports reusable FastAPI dependencies across all API routes
adhering to C:/InkFlow/docs/backend.md Section 2:
- `get_current_user`: Resolves authenticated user profile document from MongoDB.
- `get_db`: Yields active Motor async MongoDB database instance.
================================================================================
"""

from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends

from app.core.database import get_db
from app.core.security import get_current_user

__all__ = ["get_current_user", "get_db"]
