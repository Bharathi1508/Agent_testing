"""HEAAP Assurance Dashboard API - Phase 21.2."""

from fastapi import FastAPI

from app.api.routes.assurance_dashboard import (
    router as assurance_router,
)

from app.api.routes.agent_registry_dashboard import (
    router as registry_router,
)

from app.api.routes.agent_details import (
    router as agent_details_router,
)


app = FastAPI(
    title="HEAAP Assurance Dashboard API",
    version="21.2",
    description="Read-only agent registry and assurance APIs",
)

app.include_router(assurance_router)
app.include_router(registry_router)
app.include_router(agent_details_router)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "HEAAP Dashboard",
        "version": "21.2",
    }
