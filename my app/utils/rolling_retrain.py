"""
Rolling retraining utilities
---------------------------
Implements a foundation-based rolling retrain strategy:
- If a product has >= 365 days of data, use first 365 days as the initial foundation
- Otherwise, use first 90 days as the foundation (for fresh/CSV imports)
- From the foundation end date forward, for each day:
  - train on data up to that day (inclusive)
  - generate a horizon of forecasts starting the next day
  - save forecasts with generated_at = that day

This enables: show forecasts, compare to past actuals when they arrive, retrain as new data lands.
"""

from datetime import datetime, timedelta, date
from typing import Optional

from models import db, Sale, Forecast
from models.regression import forecast_linear_regression
from sqlalchemy import func


def _to_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    return d


def rolling_retrain_product(
    product_id: int,
    foundation_days_large: int = 365,
    foundation_days_small: int = 90,
    horizon_days: int = 30,
    step_days: int = 1,
    up_to: Optional[date] = None,
) -> int:
    """
    Run rolling retraining for a single product from foundation window to up_to date.

    Args:
        product_id: Product to process
        foundation_days_large: Days used as foundation when >= this many days of history exist
        foundation_days_small: Days used as foundation when history is shorter
        horizon_days: Forecast horizon per generation point
        step_days: Advance between generation points (1 = daily)
        up_to: Last generation date to process (defaults to min(today, max sale date))

    Returns:
        Number of forecast records created
    """
    created = 0

    # Determine dataset range for this product
    min_date = db.session.query(func.min(func.date(Sale.sale_date))).filter_by(product_id=product_id).scalar()
    max_date = db.session.query(func.max(func.date(Sale.sale_date))).filter_by(product_id=product_id).scalar()
    if not min_date or not max_date:
        return 0

    # Convert strings if needed
    if isinstance(min_date, str):
        min_date = datetime.strptime(min_date, "%Y-%m-%d").date()
    if isinstance(max_date, str):
        max_date = datetime.strptime(max_date, "%Y-%m-%d").date()

    # Resolve up_to
    today = datetime.now().date()
    if up_to is None:
        up_to = min(today, max_date)

    # Determine foundation length based on available days
    total_days = (up_to - min_date).days + 1
    foundation_days = foundation_days_large if total_days >= foundation_days_large else foundation_days_small
    foundation_end = min_date + timedelta(days=foundation_days - 1)

    # If foundation end is after up_to, nothing to do yet
    if foundation_end > up_to:
        return 0

    # Resume from last generated_at if exists
    last_gen = db.session.query(func.max(Forecast.generated_at)).filter(
        Forecast.product_id == product_id
    ).scalar()
    if isinstance(last_gen, str):
        last_gen = datetime.strptime(last_gen, "%Y-%m-%d").date()

    start_gen = foundation_end
    if last_gen:
        # continue from the next day after last generation
        start_gen = max(start_gen, _to_date(last_gen) + timedelta(days=step_days))

    gen_date = start_gen
    while gen_date <= up_to:
        # Generate horizon forecasts from the next day
        try:
            forecast_list = forecast_linear_regression(
                db_conn=db.engine,
                product_id=product_id,
                days_ahead=horizon_days,
                start_date=gen_date + timedelta(days=1),
                training_end_date=gen_date,
            )

            # If error dict returned
            if isinstance(forecast_list, dict) and 'error' in forecast_list:
                gen_date += timedelta(days=step_days)
                continue

            if isinstance(forecast_list, list) and forecast_list:
                # Optional: avoid duplicates for same generated_at
                # We won't delete broadly to keep history; ensure exact duplicates are skipped
                for item in forecast_list:
                    fdate = item['date']
                    if isinstance(fdate, str):
                        fdate = datetime.strptime(fdate, "%Y-%m-%d").date()

                    # Check for existing exact record
                    exists = db.session.query(Forecast.id).filter(
                        Forecast.product_id == product_id,
                        db.func.date(Forecast.forecast_date) == fdate,
                        Forecast.generated_at == gen_date,
                    ).first()
                    if exists:
                        continue

                    rec = Forecast(
                        product_id=product_id,
                        forecast_date=fdate,
                        predicted_quantity=item['prediction'],
                        confidence_lower=item.get('confidence_lower'),
                        confidence_upper=item.get('confidence_upper'),
                        model_used=item.get('model', 'ENHANCED_LINEAR_REGRESSION'),
                        aggregation_level='daily',
                        period_key=fdate.strftime('%Y-%m-%d'),
                        mae=item.get('mae'),
                        rmse=item.get('rmse'),
                        generated_at=gen_date,
                    )
                    db.session.add(rec)
                    created += 1

                db.session.commit()

        except Exception:
            db.session.rollback()
            # skip to next generation date on error
        finally:
            gen_date += timedelta(days=step_days)

    return created


def rolling_retrain_all(
    foundation_days_large: int = 365,
    foundation_days_small: int = 90,
    horizon_days: int = 30,
    step_days: int = 1,
    up_to: Optional[date] = None,
) -> int:
    """Run rolling retraining for all products with sales."""
    from models import Product

    total_created = 0
    products = db.session.query(Product).join(Sale, Product.id == Sale.product_id).distinct().all()
    for p in products:
        total_created += rolling_retrain_product(
            p.id,
            foundation_days_large=foundation_days_large,
            foundation_days_small=foundation_days_small,
            horizon_days=horizon_days,
            step_days=step_days,
            up_to=up_to,
        )
    return total_created
