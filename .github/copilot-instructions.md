# Copilot Instructions for Predictive Sales & Restocking Dashboard

This is a Flask-based inventory forecasting system built with an application factory pattern and modular blueprint architecture.

## Quick Start

### Development Setup
```powershell
# Windows PowerShell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r "my app/requirements.txt"
cd "my app"
python run_dev.py
```

Open: http://127.0.0.1:5000 | Default login: admin / admin123 (change immediately)

### Environment Configuration
Create `.env` in `my app/` with:
```env
FLASK_ENV=development
SECRET_KEY=your-secure-random-value
DATABASE_URL=postgresql://user:pass@host:5432/dbname
JWT_SECRET_KEY=your-jwt-secret-value
LOCAL_SQLITE_FALLBACK=1  # Fallback to SQLite if PostgreSQL unreachable (dev only)
```

## Build, Test & Lint

**Currently no test suite exists.** Add pytest in requirements.txt to implement tests.

### Running the Application
```powershell
cd "my app"
python run_dev.py                    # Development server (auto-reload)
python wsgi.py                       # Production WSGI entry point
gunicorn --threads 4 wsgi:app        # Production (used in Render)
```

### Database Commands
```powershell
# From "my app" directory
python auto_migrate.py               # Auto-migrate schema (runs on app startup)
python reset_database.py             # Drop and recreate all tables
python load_data.py                  # Load sales CSV data
python regenerate_forecasts.py       # Recompute forecasts for all products
```

### Deployment (Render)
```bash
# render.yaml already configured for production deployment
# Render provisions PostgreSQL and injects DATABASE_URL automatically
```

## High-Level Architecture

### Application Structure
```
my app/
├── app.py                 # Application factory (Flask setup, extensions init)
├── config.py              # Environment-based configuration (Dev/Prod/Test)
├── run_dev.py             # Development server launcher
├── wsgi.py                # Gunicorn entry point
├── models/
│   ├── __init__.py        # SQLAlchemy ORM (User, Product, Sale models)
│   ├── arima.py           # ARIMA forecasting models
│   └── regression.py      # Linear/exponential regression forecasting
├── blueprints/            # Modular route handlers
│   ├── auth/              # Login, logout, password change
│   ├── main/              # Dashboard, inventory, forecasts UI
│   ├── api/               # REST endpoints (data, analytics, preferences)
│   └── mobile/            # Mobile API (JWT-secured, exempt from CSRF/rate limits)
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, JS, images
├── utils/                 # Utilities
│   ├── activity_logger.py # Event logging
│   ├── forecast_*         # Forecast generation, evaluation, retraining
│   ├── batch_manager.py   # Batch processing
│   └── populate_*.py      # Data seeding utilities
└── data/                  # Sample CSV files (sales history)
```

### Core Flow
1. **app.py (Application Factory)**: Initializes Flask with extensions (SQLAlchemy, JWT, CSRF, rate limiter).
2. **Blueprints**: Routes separated by domain—auth (login/logout), main (UI), api (REST), mobile (mobile API).
3. **Models**: Product, Sale, User entities with relationships; forecasting models (ARIMA, regression).
4. **Forecasting**: Utilities generate forecasts on-demand or via background jobs (regenerate_forecasts.py).
5. **Security**: CSRF on web forms, JWT on mobile API, rate limiting per IP, account lockouts after 5 failed logins.

### Database
- **Production**: PostgreSQL (auto-provisioned on Render).
- **Development**: PostgreSQL (or fallback to SQLite if unreachable via `LOCAL_SQLITE_FALLBACK=1`).
- **Auto-migration**: app.py runs auto-migration on startup to add missing columns (e.g., `used_for_training` on sale table).

## Key Conventions

### API Response Format (REST)
All `/api/` endpoints return JSON with `success`, `data`, and optional `error` fields:
```python
return {'success': True, 'data': {...}}, 200
return {'success': False, 'error': 'reason'}, 400
```

### Forecasting Pipeline
1. **Data Ingestion**: CSV uploaded via `upload_csv_data.py` → parsed and inserted into `sale` table.
2. **Model Training**: `model_trainer.py` trains ARIMA and regression models on historical data.
3. **Forecast Generation**: `forecast_generator.py` predicts next 7 (or configurable) days of sales per product.
4. **Accuracy Evaluation**: `forecast_evaluator.py` computes MAPE; accuracy threshold: 80% (configurable).

### Password Security & Account Lockout
- Minimum 8 characters, uppercase, lowercase, number required.
- Account locks after 5 failed login attempts for 15 minutes.
- Default admin user created on first run; `force_password_change` flag enforces immediate password reset.

### Rate Limiting
- **Web (dev)**: 2000 per day, 500 per hour; (prod): 200 per day, 50 per hour.
- **Mobile API**: Rate limiting and CSRF exempted (JWT authentication sufficient).
- Limits use client IP via ProxyFix (handles Render reverse proxy correctly).

### CORS & Mobile Support
- **Development**: Allows localhost:3000, localhost:5000, and local network IPs (192.168.x.x, 10.x.x.x).
- **Production**: Only HTTPS origins (Render deployment URL, optional FRONTEND_URL env var).

### Configuration Hierarchy
1. Base config (Config class).
2. Environment override (DevelopmentConfig, ProductionConfig, TestingConfig).
3. Environment variables (override via `.env`).

### SQL Auto-Migration (app.py)
On startup, app.py checks for missing columns in `sale` table and adds them if needed. This pattern replaces traditional Alembic migrations for this lightweight use case.

### Version Injection
Git commit hash injected into Jinja2 globals as `static_ver` for CSS/JS cache busting on every deploy.

## Important Implementation Notes

### SQLAlchemy Connection Hardening (Production)
Render PostgreSQL connections require SSL and keepalives. app.py automatically configures:
```python
sslmode='require', connect_timeout=10, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5
```

### Fallback to Local SQLite (Development)
If `LOCAL_SQLITE_FALLBACK=1` and PostgreSQL is unreachable, app.py automatically falls back to SQLite:
```
instance/local_dev.db
```

### Blueprint Exemptions
- **Mobile API** (`blueprints/mobile/`): Exempt from CSRF protection (uses JWT) and rate limiting (JWT already protects).
- **Auth Blueprint**: Password validation enforced on create/change via `User.validate_password_strength()`.

### Forecasting Accuracy & Restock Alerts
- Products with forecast accuracy < 80% are flagged as "unreliable predictions."
- Restock recommendation: current stock < (average daily sales × 7 days threshold).
- `RESTOCK_THRESHOLD_DAYS=7` and `ACCURACY_THRESHOLD=0.80` configurable in config.py.

### Admin & Owner Protection
- Sole owner role cannot be demoted or deleted (protected by `is_owner` flag).
- Owner has all admin privileges plus account recovery controls.

## When Adding Features

### New Endpoint?
1. Create route in appropriate blueprint (auth, main, api, or mobile).
2. If data-driven, add model to models/__init__.py.
3. If forecasting-related, leverage models/arima.py or models/regression.py.
4. Return API responses in standard format: `{'success': True, 'data': {...}}`.

### New Database Column?
1. Add to model in models/__init__.py.
2. Optional: auto-migrate pattern already handles app startup. No Alembic needed unless multi-column transactions required.

### New Forecast Model?
1. Create in models/ (e.g., models/prophet.py).
2. Implement predict(product_id, days) returning list of (date, prediction) tuples.
3. Integrate into forecast_generator.py.

### Mobile API Endpoint?
- Place in blueprints/mobile/routes.py.
- Use JWT tokens (automatic via @jwt_required()).
- Do NOT add CSRF or rate limiting (already exempted).

## Common Tasks

### Test Email Notifications (if added)
Configure MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD in config.py.

### Enable Redis for Rate Limiting (Production Scaling)
Set `RATELIMIT_STORAGE_URI=redis://...` in production config.

### Audit User Activity
Check utils/activity_logger.py for logging hooks; integrate into auth routes and API endpoints.

### Debug Database Queries
Enable Flask-SQLAlchemy query logging:
```python
app.config['SQLALCHEMY_ECHO'] = True
```

## Troubleshooting

### "PostgreSQL unreachable"
1. Check DATABASE_URL in .env.
2. Enable LOCAL_SQLITE_FALLBACK=1 for local dev (falls back to instance/local_dev.db).
3. Verify Render PostgreSQL is provisioned and running.

### "CSRF token validation failed"
1. Mobile API calls should use JWT, not cookies.
2. Web forms must include `{{ csrf_token() }}` in hidden field.

### "Forecast data missing"
1. Ensure sales data loaded: `python load_data.py`.
2. Run `python regenerate_forecasts.py`.
3. Check forecast_evaluator logs for accuracy issues.

### "Default admin login not working"
1. Check app.py console for auto-created admin credentials.
2. If lost, run `python reset_database.py` to recreate.

---

**Last Updated**: 2025  
**Project Scope**: Academic capstone (educational and approved client operations only)
