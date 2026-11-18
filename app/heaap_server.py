from app.main import app
from app.api.routes.supervisor_metadata_routes import router

required = {
    "/api/supervisor-metadata/select",
    "/api/supervisor-metadata/validate",
    "/api/supervisor-metadata/bulk-validate",
}

existing = {
    getattr(route, "path", None)
    for route in app.routes
}

for route in router.routes:
    if route.path in required and route.path not in existing:
        app.add_api_route(
            route.path,
            route.endpoint,
            methods=list(route.methods),
            name=route.name,
        )
        existing.add(route.path)

from app.api.routes.heaap_pipeline_routes import router as heaap_pipeline_router
app.include_router(heaap_pipeline_router)

from app.api.routes.heaap_pipeline_routes import (
    validate_pipeline,
    PipelineRequest,
)

@app.post(
    "/api/heaap/pipeline/validate",
    tags=["HEAAP Pipeline"],
)
def heaap_pipeline_validate_direct(request: PipelineRequest):
    return validate_pipeline(request)
