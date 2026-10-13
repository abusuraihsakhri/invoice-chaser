# Invoice Chaser

Invoice Chaser is an accounts-receivable application for managing clients and invoices, preparing payment reminders, exporting records, and tracking payment status. It combines a Next.js browser interface with a Python FastAPI backend and SQL database. Desktop (Electron) and Android (Capacitor) packaging projects are also included.

## Features

- Client and invoice management, due dates, paid/overdue states, and dashboard totals.
- Scheduled email reminders, manual sends, and customizable message tone. Email is **not** considered sent without a successful transport; console simulation requires explicit development configuration.
- Rule-based risk estimates and optional remote text-generation providers. Risk scores and response-rate estimates are **heuristics, not validated predictions**.
- PDF invoices and CSV exports (exports require authentication).
- Optional Stripe Checkout sessions; payment records are settled only after a verified Stripe webhook confirms matching invoice amount and currency.
- Optional server-configured webhook notifications for operational events.

## Deployment status and architecture

The frontend builds as static files, but **is not a standalone offline application**. Login, invoices, reminders, PDFs, payments, and storage require a running FastAPI backend. GitHub Pages cannot host the backend, scheduled jobs, database, or server-held Stripe/email credentials. No GitHub Pages deployment of a working full application has been verified.

The [GitHub releases](https://github.com/abusuraihsakhri/invoice-chaser/releases) may contain packaged desktop, Android, and backend artifacts. These clients also require a reachable backend; release artifacts are not a hosted service.

## Local development

Requires Python 3.12+, Node.js 20+ and npm. Start the backend from the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second shell:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000 and register an account. API documentation is at http://localhost:8000/docs. Development defaults to local SQLite and a random JWT signing key; tokens from a restarted development instance can become invalid. Optional integrations are inactive until configured.

To use the Compose stack, create a local untracked `.env` file in the repository root containing strong `POSTGRES_PASSWORD` and `SECRET_KEY` values. Then run `docker compose up --build`. The Compose backend runs in production mode and will not silently switch to SQLite if PostgreSQL is unavailable.

## Configuration

Keep all credentials on the **backend**. Relevant variables include:

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | `development` (default) or `production` |
| `SECRET_KEY` | Strong stable JWT signing key; required in production |
| `DATABASE_URL` | SQLAlchemy database URL (SQLite default in development) |
| `FRONTEND_URL` | Frontend address used for payment redirects |
| `CORS_ORIGINS` | Additional allowed frontend origins when configured |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Live payments and verified callbacks |
| `RESEND_API_KEY`, `EMAIL_FROM` | Transactional email via Resend |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Alternative SMTP delivery |
| `EMAIL_PROVIDER=console` | Development/test-only simulated email transport |
| `SLACK_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`, `GENERIC_WEBHOOK_URL` | Server-side alert targets |

For remote browser clients, configure the API URL under **Settings** and enable its origin in the backend CORS configuration. Use HTTPS for any internet-facing API; do not put API keys into browser-local settings or static exports. The browser application stores its login token and API URL in local storage, so use trusted devices and avoid untrusted scripts/extensions.

## Verification

```bash
cd backend
python -m pytest tests/test_api.py -v

cd ../frontend
npm ci
npm run build
```

GitHub Actions CI tests the backend and checks Next.js static export outputs. Platform-specific desktop and mobile builds are defined in the release workflow; successful compilation does not verify native packaging, notifications, payment providers, or all device/browser workflows.

## Technology and compatibility

- Backend: FastAPI, SQLAlchemy, SQLite/PostgreSQL, APScheduler, ReportLab.
- Frontend: Next.js 14, React 18, Tailwind CSS; modern Chromium, Firefox, and Safari-compatible browsers are intended.
- Desktop/mobile: Electron and Capacitor project templates. External runtime prerequisites and deployed API are required.
- Privacy: Client names, email addresses, invoices, and authentication records are stored in the configured backend database. Email and payment providers receive data needed for their configured operations. API credentials must remain server-side.

## License

The repository does not currently contain a `LICENSE` file. No reuse or distribution rights are granted by this README; the repository owner should add an explicit license if desired.
