#!/usr/bin/env python
"""Clear all data from the database tables (keep admin user only).

Removes products and ALL related/derived data so a fresh CSV upload can rebuild everything.
"""

import sys
sys.path.insert(0, '.')

from app import create_app
from models import (
    db,
    Product,
    Sale,
    Inventory,
    Forecast,
    ForecastSnapshot,
    Alert,
    DashboardMetrics,
    WebSocketSession,
    ImportLog,
    UserPreference,
    User,
    Log,
)

def main():
    app = create_app()
    with app.app_context():
        print("Clearing database tables...")

        # Delete in order of dependencies (children first)
        deleted = {}

        deleted['forecasts'] = Forecast.query.delete()
        deleted['forecast_snapshots'] = ForecastSnapshot.query.delete()
        deleted['alerts'] = Alert.query.delete()
        deleted['inventory'] = Inventory.query.delete()
        deleted['sales'] = Sale.query.delete()
        deleted['dashboard_metrics'] = DashboardMetrics.query.delete()
        deleted['websocket_sessions'] = WebSocketSession.query.delete()
        deleted['logs'] = Log.query.delete()
        deleted['import_logs'] = ImportLog.query.delete()
        deleted['user_prefs'] = UserPreference.query.delete()
        deleted['products'] = Product.query.delete()

        # Delete non-admin users only
        deleted['non_admin_users'] = User.query.filter(User.username != 'admin').delete()

        db.session.commit()

        # Report
        for k, v in deleted.items():
            print(f"✓ Deleted {v} {k.replace('_', ' ')} records")

        print("\n✅ Database cleared successfully!")
        print("✅ Admin user preserved")

        # Verify admin still exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print(f"✅ Admin user exists: {admin.username} ({admin.email})")
        else:
            print("⚠️  Warning: Admin user not found!")

if __name__ == '__main__':
    main()

