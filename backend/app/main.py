from __future__ import annotations
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.agents import router as agents_router
from app.api.v1.skills import router as skills_router
from app.api.v1.policies import router as policies_router
from app.api.v1.audits import router as audits_router
from app.api.v1.costs import router as costs_router
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
import app.domain.executions.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
import app.domain.policies.models  # noqa: F401
import app.domain.skills.models  # noqa: F401

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("governai.startup", version=settings.APP_VERSION)
    yield
    logger.info("governai.shutdown")


app = FastAPI(
    title="GovernAI",
    description="Enterprise AI-agent governance platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

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

@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
