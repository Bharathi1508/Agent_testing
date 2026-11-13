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
