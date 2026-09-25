"""Aggregates all v1 API routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    children,
    claims,
    eligibility,
    health,
    hr,
    payout_settings,
    reports,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(children.router, tags=["children"])
api_router.include_router(eligibility.router, tags=["eligibility"])
api_router.include_router(claims.router, tags=["claims"])
api_router.include_router(hr.router, tags=["hr"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(payout_settings.router, tags=["payout-settings"])
