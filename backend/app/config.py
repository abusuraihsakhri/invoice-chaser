import os
import secrets
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Invoice Chaser API"
    app_version: str = "1.0.0"
    environment: str = "production"
    debug: bool = False

    # Database: Defaults to local SQLite if postgres is not provided
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./invoice_chaser.db")

    # Security & JWT
    # If no secret key is provided, generate a secure random one for development/session safety
    secret_key: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS Allowed Origins (Web, Electron Desktop, Capacitor Android)
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
        "app://.",
    ]

    # AI Provider: 'hermes', 'openai', 'gemini', 'anthropic', 'offline'
    ai_provider: str = os.getenv("AI_PROVIDER", "hermes")
    hermes_api_key: str = os.getenv("HERMES_API_KEY", "")
    hermes_api_url: str = os.getenv("HERMES_API_URL", "https://api.hermes.com/v1/chat/completions")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Email Integrations
    email_provider: str = os.getenv("EMAIL_PROVIDER", "resend")  # 'resend', 'smtp', 'console'
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "reminders@invoicechaser.app")

    # SMTP Configuration
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_tls: bool = os.getenv("SMTP_TLS", "true").lower() in ("true", "1", "yes")

    # Stripe Payment Integration
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_publishable_key: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Outgoing Webhooks (Slack, Discord, Custom ERP)
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    discord_webhook_url: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    generic_webhook_url: str = os.getenv("GENERIC_WEBHOOK_URL", "")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")

    # App URLs
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

