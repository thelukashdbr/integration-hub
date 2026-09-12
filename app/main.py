import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import integrations
from app.api.deps import DbSession
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Integration Hub",
    description="Centralize, execute and troubleshoot integrations with external REST APIs.",
    version="0.1.0",
)

app.include_router(integrations.router)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
def health(db: DbSession) -> JSONResponse:
    # Unauthenticated on purpose: this is what an orchestrator/load balancer polls.
    # The driver error is never returned — it could expose the DB host.
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.error("health check failed: database unreachable", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return JSONResponse(content={"status": "ok"})
