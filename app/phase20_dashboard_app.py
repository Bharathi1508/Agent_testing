from app.api.routes.unified_assurance_dashboard import router as unified_assurance_router
from app.api.routes.agent_assurance_dashboard import router as assurance_dashboard_router
from app.api.routes.governance_reviews import router as governance_router
from app.api.routes.supervisor_explanations import router as supervisor_explanations_router
from app.api.routes.assurance_test_details import router as test_details_router
from app.api.routes.assurance_analytics import router as analytics_router
from app.api.routes.onboarding_review_details import router as onboarding_reviews_router
from app.api.routes.onboarding_monitoring import router as onboarding_router
from app.api.routes.agent_details import router as agent_details_router
"""HEAAP Assurance Dashboard API."""

from fastapi import FastAPI

from app.api.routes.assurance_dashboard import (
    router as assurance_router,
)

from app.api.routes.agent_registry_dashboard import (
    router as registry_router,
)


app = FastAPI(
    title="HEAAP Assurance Dashboard API",
    version="21.1",
    description="Read-only agent assurance and registry APIs",
)

app.include_router(assurance_router)
app.include_router(registry_router)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "HEAAP Dashboard",
        "version": "21.1",
    }

app.include_router(agent_details_router)

app.include_router(onboarding_router)

app.include_router(onboarding_reviews_router)

app.include_router(analytics_router)

app.include_router(test_details_router)

app.include_router(supervisor_explanations_router)

app.include_router(governance_router)

from app.api.routes.governance_approval import router as governance_approval_router
app.include_router(governance_approval_router)


# Phase 22.2 - Read-only discovered agents
from app.api.routes.agent_discovery_dashboard import (
    router as discovery_dashboard_router,
)

app.include_router(discovery_dashboard_router)

app.include_router(assurance_dashboard_router)

app.include_router(unified_assurance_router)
