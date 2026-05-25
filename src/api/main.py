"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import auth, health, simulation


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Retail Multi-Agent AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(simulation.router)


@app.get("/")
async def root() -> dict:
    return {"name": "Retail Multi-Agent AI API", "version": "0.1.0", "status": "running"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


if __name__ == "__main__":
    import uvicorn
    from src.core.config import settings

    uvicorn.run("src.api.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.API_RELOAD)
