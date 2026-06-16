"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.api.limiter import limiter

from src.api.routes import auth, forecast, health, simulation
from src.core.config import settings

logger = logging.getLogger(__name__)

# Limiter imported from src.api.limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title="Retail Multi-Agent AI API", version="0.1.0", lifespan=lifespan)

# Attach limiter so route decorators can reference app.state.limiter
app.state.limiter = limiter
from slowapi import _rate_limit_exceeded_handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middleware — CORS allowlist (P1)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,          # API uses Authorization header, not cookies
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(simulation.router)


@app.get("/")
async def root() -> dict:
    return {"name": "Retail Multi-Agent AI API", "version": "0.1.0", "status": "running"}


# ---------------------------------------------------------------------------
# Global error handler — secure (P1)
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return a generic error message; log the real exception server-side."""
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
