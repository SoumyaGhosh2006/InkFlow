"""
InkFlow API Version 1 Router Package.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
Aggregates authentication, drill/grill onboarding, rewrite pipeline, analytics,
and billing/payment endpoints into a unified FastAPI APIRouter strictly
adhering to C:/InkFlow/docs/backend.md Section 8:
- /api/v1/auth (auth sync, me)
- /api/v1/grill (prompts, analyze)
- /api/v1/rewrite (pipeline, accept)
- /api/v1/analytics (evolution, history)
- /api/v1/payments (create-order, verify, webhook)
================================================================================
"""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.grill import router as grill_router
from app.api.v1.rewrite import router as rewrite_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.payments import router as payments_router

api_v1_router = APIRouter()

# Register sub-routers adhering to REST API Endpoints Specification (docs/backend.md Section 8)
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(grill_router, prefix="/grill", tags=["Timed Drill & Onboarding"])
api_v1_router.include_router(grill_router, prefix="/drill", include_in_schema=False)  # Alias
api_v1_router.include_router(rewrite_router, prefix="/rewrite", tags=["Rewrite Pipeline"])
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics & Evolution"])
api_v1_router.include_router(payments_router, prefix="/payments", tags=["Payments & Subscriptions"])
