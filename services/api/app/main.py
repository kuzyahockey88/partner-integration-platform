from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from .core.config import settings
#from .core.database import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    logger.info(f"Database URL: {settings.database_url}")
    #await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down application...")
    #await close_db()
    logger.info("Database connection closed")

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": settings.project_name,
        "version": settings.version,
        "status": "running",
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.project_name,
    }