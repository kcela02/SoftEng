# Predictive Sales & Restocking Dashboard System

## Description
The Predictive Sales & Restocking Dashboard System is a data-driven inventory management web application built with Flask.

It uses historical sales data, trend patterns, and forecasting models to:
- estimate short-term demand,
- suggest restocking actions,
- and help reduce stockouts and overstock situations.

The system includes a browser dashboard for monitoring sales and inventory, plus API endpoints for mobile integration.

## Objectives
- Automate sales forecasting for top-selling products.
- Improve restocking timing with forecast-based recommendations.
- Provide clear visualizations for inventory and sales performance.
- Reduce manual inventory decision-making effort.
- Maintain a modular architecture that can be extended later.

## Scope
- CSV-based sales ingestion and processing.
- Forecasting using Regression and ARIMA-related utilities.
- Web dashboard for products, forecasts, reports, and settings.
- API routes for data access and mobile workflows.
- Basic operational safeguards (authentication, CSRF, rate limiting).

## Limitations
- Forecast quality depends heavily on data quality and coverage.
- Sudden market events can reduce prediction reliability.
- Highly irregular products may need custom modeling logic.
- No direct supplier-ordering integration.

## Tech Stack
- Backend: Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Limiter, Flask-JWT-Extended
- Data/ML: pandas, numpy, scikit-learn, statsmodels
- Database: PostgreSQL (production), optional SQLite fallback in development
- Deployment: Render + Gunicorn + WhiteNoise

## Repository Structure
```text
SoftEng/
├── README.md
├── render.yaml
├── Document/
└── my app/
	├── app.py
	├── config.py
	├── run_dev.py
	├── wsgi.py
	├── requirements.txt
	├── data/
	├── models/
	├── blueprints/
	├── templates/
	├── static/
	└── utils/
```

## Local Setup

### 1) Create and activate virtual environment (Windows PowerShell)
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies
```powershell
pip install -r "my app/requirements.txt"
```

### 3) Configure environment variables
Create a .env file inside my app with values similar to:

```env
FLASK_ENV=development
SECRET_KEY=replace-with-a-secure-random-value
DATABASE_URL=postgresql://username:password@host:5432/database
JWT_SECRET_KEY=replace-with-a-secure-random-value
```

Notes:
- The app normalizes older postgres:// URLs automatically.
- In development, LOCAL_SQLITE_FALLBACK=1 can be used to fall back to SQLite when PostgreSQL is unreachable.

### 4) Run the app
From the my app directory:

```powershell
cd "my app"
python run_dev.py
```

Open: http://127.0.0.1:5000

A default admin account is created automatically on first run if missing.
Change the initial admin password immediately after first login.

## Deployment (Render)
This repository already includes render.yaml configured to:
- use the my app directory as root,
- install dependencies from requirements.txt,
- run Gunicorn with wsgi:app,
- provision a PostgreSQL database and inject DATABASE_URL.

Start command used in production:

```bash
gunicorn --threads 4 --bind 0.0.0.0:$PORT wsgi:app
```

## Data and Operations
- Sales/history CSV samples are located in my app/data.
- Utility scripts in my app support migration, forecasting, retraining, and data import tasks.
- Database tables are created automatically on startup; lightweight column migration is also handled in app startup.

## Security and Reliability Notes
- CSRF protection enabled for web forms.
- Rate limiting enabled (with higher limits in development).
- JWT authentication used for mobile API routes.
- ProxyFix and PostgreSQL connection hardening are applied for production reliability.

## Academic Use
This system was developed as an academic capstone project in collaboration with a client partner.
Use is limited to educational purposes and approved client operations within the agreed project scope.
Ownership, deployment rights, and any commercial use are governed by the agreement between the academic team, institution, and client.
