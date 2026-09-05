from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager, suppress

import structlog
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.domain.automations.engine import run_automation_engine
from app.api.v1.agents import router as agents_router
from app.api.v1.skills import router as skills_router
from app.api.v1.policies import router as policies_router
from app.api.v1.audits import router as audits_router
from app.api.v1.costs import router as costs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.automations import router as automations_router
from app.api.v1.automations import runs_router as automation_runs_router
from app.api.v1.executions import router as executions_router

# Import every domain's ORM models so SQLAlchemy's mapper registry knows
# about all tables at startup, regardless of which routers are wired up.
# Without this, a cross-domain foreign key (e.g. agents.owner_id ->
# profiles.id) fails with NoReferencedTableError the first time it's
# actually flushed, because the referenced table's model was never
# imported by anything on the request path.
import app.domain.agents.models  # noqa: F401
import app.domain.audit.models  # noqa: F401
import app.domain.auth.models  # noqa: F401
import app.domain.costs.models  # noqa: F401
import app.domain.documents.models  # noqa: F401
import app.domain.automations.models  # noqa: F401
import app.domain.executions.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
import app.domain.policies.models  # noqa: F401
import app.domain.skills.models  # noqa: F401

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle.

    The automation engine is the one subscriber that lives as long as the
    process — every other bus subscriber is an SSE connection that comes and
    goes. It is started here so rules are evaluated whether or not anyone has
    the console open: an automation that only fires while somebody is watching
    would be worthless.
    """
    logger.info("governai.startup", version=settings.APP_VERSION)

    engine_task = asyncio.create_task(run_automation_engine())

    try:
        yield
    finally:
        engine_task.cancel()
        # Wait for the cancellation to land so the subscription is removed
        # from the bus rather than leaking on every reload.
        with suppress(asyncio.CancelledError):
            await engine_task
        logger.info("governai.shutdown")


app = FastAPI(
    title="GovernAI",
    description="Enterprise AI-agent governance platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

class UnhandledErrorMiddleware(BaseHTTPMiddleware):
    """Turn an unhandled exception into a JSON 500 *inside* the CORS layer.

    Starlette's own ServerErrorMiddleware sits outside every user middleware,
    so a 500 it produces never passes back through CORSMiddleware and carries
    no `Access-Control-Allow-Origin` header. The browser then rejects the
    response before any JavaScript sees it, and `fetch` rejects with the
    useless "Failed to fetch" — the real error, and its status code, are
    invisible in the console during exactly the incident you most need them.

    Catching here means the response is generated inside CORS, so the headers
    are added normally and the frontend can show what actually went wrong.
    The exception is still logged, and re-raised nowhere: the traceback is
    already on its way to the logger below.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                "governai.unhandled_error",
                path=str(request.url.path),
                method=request.method,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "data": None,
                    "meta": None,
                    "errors": [
                        {
                            "type": "internal_error",
                            "title": "Internal Server Error",
                            "status": 500,
                            "detail": (
                                "The server failed to handle this request. "
                                "Check the API logs for the traceback."
                            ),
                            "instance": str(request.url.path),
                        }
                    ],
                },
            )


# Added before CORS so that CORS ends up OUTSIDE it: the last middleware added
# is the outermost, and CORS must wrap this one to put its headers on the 500.
app.add_middleware(UnhandledErrorMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router, prefix="/api/v1", tags=["Agents"])
app.include_router(skills_router, prefix="/api/v1", tags=["Skills"])
app.include_router(policies_router, prefix="/api/v1", tags=["Policies"])
app.include_router(audits_router, prefix="/api/v1", tags=["Audits"])
app.include_router(executions_router, prefix="/api/v1", tags=["Executions"])
app.include_router(costs_router, prefix="/api/v1", tags=["Costs"])
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(events_router, prefix="/api/v1", tags=["Events"])
app.include_router(automations_router, prefix="/api/v1", tags=["Automations"])
app.include_router(automation_runs_router, prefix="/api/v1", tags=["Automations"])

@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
