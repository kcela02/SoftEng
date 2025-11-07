# 📊 Predictive Sales & Restocking Dashboard

An intelligent inventory management system with AI-powered demand forecasting, real-time alerts, and automated restock recommendations.

## 🚀 Key Features

### 📈 Intelligent Forecasting
- **Multi-Horizon Predictions**: 1-day, 7-day, and 30-day demand forecasts
- **Automated Model Training**: Auto-retrains on new data uploads
- **Forecast Accuracy Tracking**: Real-time accuracy metrics (MAPE-based)
- **Batch Processing Pipeline**: Efficient forecasting for all products

### 🎯 Smart Restock Alerts
- **Urgency-Based Alerts**: CRITICAL (1-day), HIGH (7-day), MEDIUM (30-day)
- **Recommended Order Quantities**: Calculated with 20% safety margin
- **Multi-Horizon Analysis**: Shows which time periods are at risk
- **One-Click Restock**: Quick inventory adjustment workflow

### 📁 Simplified Data Import
- **⭐ Unified Sales CSV**: One file for sales + products + inventory
  - Perfect for POS system exports
  - Auto-creates products
  - Natural business workflow
- **Legacy Formats**: Still supports separate CSV files
- **Validation & Deduplication**: Automatic duplicate detection
- **Detailed Import Reports**: Shows success/skipped/failed rows

### 📊 Real-Time Dashboard
- **WebSocket Live Updates**: <500ms latency for metrics
- **Interactive Charts**: Sales trends, monthly performance, top products
- **Tab-Based Interface**: Overview, Forecasting, Products, Reports, Settings
- **Period Filtering**: 7-day, 30-day, 3-month, 6-month, 1-year, custom ranges

### 🔔 Alert System
- **Real-Time Notifications**: WebSocket-powered instant alerts
- **Acknowledgment Tracking**: Mark alerts as resolved
- **Alert History**: Full audit trail in database
- **Severity Levels**: CRITICAL, HIGH, MEDIUM

## 📦 Quick Start

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd "my app"
```

2. **Create virtual environment**
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Initialize database**
```bash
python migrate_db.py
```

5. **Run the server**
```bash
python app.py
```

6. **Access dashboard**
Open browser: `http://127.0.0.1:5000`
Login: `admin` / `admin123`

## 📄 CSV Import Formats

### ⭐ Recommended: Unified Sales CSV

```csv
product_name,category,unit_cost,quantity_sold,sale_price,sale_date,stock_after_sale
Laptop,Electronics,500.00,2,599.99,2025-10-28,48
Mouse,Electronics,25.00,5,29.99,2025-10-28,115
```

**Benefits:**
✅ One file does everything  
✅ Auto-creates products  
✅ Updates inventory automatically  
✅ Perfect for daily POS exports

See `sample_unified_sales.csv` for a complete example.

### Alternative: Separate Files

- **Products CSV**: `name, category, unit_cost, current_stock`
- **Sales CSV**: `product_id, quantity, price, sale_date`
- **Inventory CSV**: `product_id, quantity, operation, date`

See `SAMPLE_DATA_FORMAT.md` for detailed format specifications.

## 🛠️ Technology Stack

- **Backend**: Flask, SQLAlchemy, Flask-SocketIO
- **Frontend**: Vanilla JavaScript, Chart.js, Socket.IO client
- **Forecasting**: NumPy, SciPy, Statsmodels (Linear Regression)
- **Real-Time**: WebSocket (eventlet)
- **Database**: SQLite (development), PostgreSQL-ready (production)

## 📂 Project Structure

```
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── models/                     # Database models
│   ├── __init__.py            # ORM models (Product, Sale, Forecast, etc.)
│   ├── arima.py               # ARIMA forecasting (future)
│   ├── regression.py          # Linear regression forecasting
│   └── utils.py               # Utility functions
├── blueprints/api/            # API endpoints
│   └── routes.py              # REST API routes
├── templates/                 # HTML templates
│   └── admin.html             # Main dashboard UI
├── static/                    # Static assets
│   ├── app.js                 # Frontend JavaScript
│   └── css/main.css           # Stylesheets
├── utils/                     # Utility modules
│   ├── model_trainer.py       # Automated forecasting pipeline
│   └── forecast_evaluator.py # Accuracy calculation
├── data/                      # Data storage
│   └── schema.sql             # Database schema
└── reports/                   # Generated reports

```

## 🎯 Usage Workflow

1. **Import Data**
   - Go to Products tab
   - Select "Unified Sales" format
   - Upload CSV from POS system
   - System auto-trains forecasting models

2. **Monitor Dashboard**
   - Overview tab shows key metrics
   - Restock alerts appear automatically
   - Charts update in real-time

3. **Review Forecasts**
   - Forecasting tab shows accuracy metrics
   - 7-day demand forecast table
   - Multi-horizon predictions

4. **Take Action**
   - Click "Order Now" on alerts
   - Adjust inventory quantities
   - System recalculates forecasts

5. **Generate Reports**
   - Reports tab for analytics
   - Export data as CSV
   - Track import history

## 📊 Forecasting Methodology

### Linear Regression Model
- **Training**: Uses historical sales data (minimum 7 days)
- **Features**: Day-of-week, trend, moving averages
- **Horizons**: 1-day, 7-day, 30-day predictions
- **Accuracy**: MAPE-based (Mean Absolute Percentage Error)
- **Auto-Retrain**: Triggers on new sales data uploads

### Restock Logic
```
CRITICAL: current_stock < forecast_1day
HIGH:     current_stock < forecast_7day
MEDIUM:   current_stock < forecast_30day

Recommended Order Qty = forecast_7day × 1.2 (20% safety margin)
```

## 🔧 Configuration

Edit `config.py` for settings:

```python
DATABASE_URI = 'sqlite:///sales_dashboard.db'
SECRET_KEY = 'your-secret-key'
DEBUG = True
WEBSOCKET_ENABLED = True
```

## 📝 Documentation

- **IMPORT_GUIDE.txt**: Detailed CSV format guide
- **SAMPLE_DATA_FORMAT.md**: CSV specifications and examples
- **ARCHITECTURAL_RECOMMENDATIONS.md**: Full implementation roadmap
- **PHASE1B_IMPLEMENTATION.md**: CSV validation documentation

## 🚀 Production Deployment

For production use:
1. Set `DEBUG = False` in `config.py`
2. Use PostgreSQL instead of SQLite
3. Configure proper SECRET_KEY
4. Enable HTTPS
5. Set up email notifications (see roadmap)
6. Implement backup/restore (see roadmap)

## 📈 Roadmap

- ✅ Phase 1: CSV Validation & Deduplication
- ✅ Phase 2: Automated Forecasting & Enhanced Alerts
- ⬜ Phase 3: Email Notifications
- ⬜ Phase 4: Seasonal Pattern Detection
- ⬜ Phase 5: ARIMA Models
- ⬜ Phase 6: Multi-Store Support

See `ARCHITECTURAL_RECOMMENDATIONS.md` for complete roadmap.

## 🤝 Contributing

This is a private project. For questions or suggestions, contact the development team.

## 📄 License

Proprietary - All rights reserved

---

**Built with ❤️ for intelligent inventory management**