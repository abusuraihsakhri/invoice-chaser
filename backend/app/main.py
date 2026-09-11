import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import (
    auth,
    clients,
    invoices,
    reminders,
    dashboard,
    intelligence,
    integrations,
)
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("invoice_chaser.main")

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Invoice Chaser API v%s", settings.app_version)
    start_scheduler()
    yield
    logger.info("Stopping Invoice Chaser API")
    stop_scheduler()


app = FastAPI(
    title="Invoice Chaser API",
    version=settings.app_version,
    description="Cross-platform intelligent accounts receivable automation engine with payment & notification integrations.",
    lifespan=lifespan,
)

# Cross-Platform CORS (supports Web, Electron Desktop, and Android Capacitor webviews)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.0\.2\.2|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(invoices.router)
app.include_router(reminders.router)
app.include_router(dashboard.router)
app.include_router(intelligence.router)
app.include_router(integrations.router)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": settings.app_version,
        "database": engine.dialect.name,
        "ai_provider": settings.ai_provider,
        "email_configured": bool(settings.resend_api_key or settings.smtp_host),
        "stripe_configured": bool(settings.stripe_secret_key),
    }

