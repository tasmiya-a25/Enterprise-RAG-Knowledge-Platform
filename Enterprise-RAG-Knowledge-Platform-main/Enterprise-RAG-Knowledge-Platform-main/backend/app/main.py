from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.database.session import Base, engine
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.utils.logger import logger

# Ensure all models are registered on Base.metadata before create_all().
import app.models  # noqa: F401

from app.api.routes import auth, users, documents, chat, feedback

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Day-1 build uses create_all for simplicity. Alembic scaffolding is
    # included (see backend/alembic/) for schema migrations going forward --
    # switch to `alembic upgrade head` in deployment once the schema stabilizes.
    Base.metadata.create_all(bind=engine)
    logger.info(f"{settings.APP_NAME} started (env={settings.ENV})")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Enterprise RAG Knowledge Platform API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


@app.get("/health", tags=["monitoring"])
def health():
    return {"status": "ok"}


@app.get("/metrics", tags=["monitoring"])
def metrics():
    # Placeholder for Prometheus-style metrics. Wiring `prometheus-fastapi-instrumentator`
    # is a drop-in roadmap item -- see docs/ROADMAP.md.
    return {"status": "metrics endpoint placeholder"}


api_prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(chat.router, prefix=api_prefix)
app.include_router(feedback.router, prefix=api_prefix)
