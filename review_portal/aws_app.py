from __future__ import annotations

from fastapi import FastAPI

from .app import create_app


app: FastAPI = create_app()

# The local health endpoint includes a filesystem path for diagnostics. Public AWS
# deployments use a minimal health response so internal server paths are not exposed.
for route in list(app.router.routes):
    if getattr(route, "path", None) == "/health":
        app.router.routes.remove(route)


@app.get("/health")
async def public_health() -> dict[str, bool]:
    return {"ok": True}
