# blueprints/mobile/routes.py
"""
Mobile REST API — JWT-authenticated endpoints consumed by the Android app.

Architecture
------------
Web (browser)  → /api/*        → session cookies (Flask-Login)
Mobile (app)   → /api/mobile/* → Bearer tokens   (Flask-JWT-Extended)

Both paths read/write the same PostgreSQL database via SQLAlchemy models.

Authentication flow (mobile)
-----------------------------
1.  POST /api/mobile/auth/login   { "username": ..., "password": ... }
    ← { "access_token": "<1h JWT>", "refresh_token": "<30d JWT>", "user": {...} }

2.  All subsequent requests include:
    Authorization: Bearer <access_token>

3.  When access_token expires (1 h):
    POST /api/mobile/auth/refresh
    Authorization: Bearer <refresh_token>
    ← { "access_token": "<new 1h JWT>" }
"""

from flask import jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from models import db, User, Product, Sale, Alert, Forecast, InventoryBatch
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from . import mobile_bp


# ─────────────────────────────────────────────────────── helpers ────────────

def _current_user():
    """Return the User object whose id is stored in the JWT."""
    user_id = get_jwt_identity()
    return db.session.get(User, user_id)


def _error(message, status=400):
    return jsonify({'success': False, 'error': message}), status


def _ok(data=None, **kwargs):
    payload = {'success': True}
    if data is not None:
        payload['data'] = data
    payload.update(kwargs)
    return jsonify(payload), 200


# ══════════════════════════════════════════════════════════════════════════════
# Auth endpoints  (no JWT required — these ARE the login routes)
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/auth/login', methods=['POST'])
def login():
    """
    Authenticate with username + password, receive JWT tokens.

    Request body (JSON):
        { "username": "admin", "password": "secret" }

    Response:
        {
          "success": true,
          "access_token":  "<1-hour JWT>",
          "refresh_token": "<30-day JWT>",
          "user": { "id": 1, "username": "admin", "role": "admin", ... }
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return _error('Request body must be JSON')

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return _error('username and password are required')

    user = User.query.filter_by(username=username).first()
    if not user:
        return _error('Invalid credentials', 401)

    # Account lockout check (same logic as the web login)
    if user.is_account_locked():
        remaining = int((user.account_locked_until - datetime.utcnow()).total_seconds() / 60)
        return _error(f'Account locked. Try again in {remaining} minutes.', 403)

    if not user.check_password(password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        return _error('Invalid credentials', 401)

    # Successful login — reset failure counter
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.last_login = datetime.utcnow()
    db.session.commit()

    access_token  = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'success': True,
        'access_token':  access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
    }), 200


@mobile_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Exchange a valid refresh token for a new access token.

    Header:  Authorization: Bearer <refresh_token>
    Returns: { "success": true, "access_token": "<new 1h JWT>" }
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)
    return _ok(access_token=create_access_token(identity=user.id))


@mobile_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def me():
    """Return the authenticated user's profile."""
    user = _current_user()
    if not user:
        return _error('User not found', 401)
    return _ok(user.to_dict())


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard summary
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """
    Quick-glance numbers for the mobile home screen.

    Response includes:
    - revenue today / this week / this month
    - total products, low-stock count (≤ 10 units)
    - active unacknowledged alerts
    - top 5 best-selling products (last 30 days)
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    now = datetime.utcnow()
    today_start  = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start   = today_start - timedelta(days=now.weekday())
    month_start  = today_start.replace(day=1)

    def revenue_since(dt):
        row = db.session.query(func.sum(Sale.quantity * Sale.price)) \
                        .filter(Sale.sale_date >= dt).scalar()
        return round(float(row or 0), 2)

    total_products  = Product.query.filter_by(is_fake=False).count()
    low_stock_count = Product.query.filter(
        Product.is_fake == False,
        Product.current_stock <= 10
    ).count()

    active_alerts = Alert.query.filter_by(
        is_active=True, is_acknowledged=False
    ).count()

    # Top 5 products last 30 days
    thirty_days_ago = now - timedelta(days=30)
    top_products_raw = (
        db.session.query(
            Product.id, Product.name,
            func.sum(Sale.quantity).label('units_sold'),
            func.sum(Sale.quantity * Sale.price).label('revenue')
        )
        .join(Sale, Sale.product_id == Product.id)
        .filter(Sale.sale_date >= thirty_days_ago, Product.is_fake == False)
        .group_by(Product.id, Product.name)
        .order_by(desc('units_sold'))
        .limit(5)
        .all()
    )

    top_products = [
        {
            'product_id':   r.id,
            'product_name': r.name,
            'units_sold':   int(r.units_sold or 0),
            'revenue':      round(float(r.revenue or 0), 2),
        }
        for r in top_products_raw
    ]

    return _ok({
        'revenue': {
            'today':  revenue_since(today_start),
            'week':   revenue_since(week_start),
            'month':  revenue_since(month_start),
        },
        'products': {
            'total':      total_products,
            'low_stock':  low_stock_count,
        },
        'active_alerts':  active_alerts,
        'top_products':   top_products,
        'generated_at':   now.isoformat(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# Products
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/products', methods=['GET'])
@jwt_required()
def products():
    """
    Paginated product catalogue.

    Query params:
        page     (int, default 1)
        limit    (int, default 20, max 100)
        search   (str) — filters name / category
        sort     (str) — "name" | "stock" | "cost"  (default: name)
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    page   = max(1, request.args.get('page',  1,  type=int))
    limit  = min(100, max(1, request.args.get('limit', 20, type=int)))
    search = (request.args.get('search') or '').strip()
    sort   = request.args.get('sort', 'name')

    q = Product.query.filter_by(is_fake=False)

    if search:
        like = f'%{search}%'
        q = q.filter(
            (Product.name.ilike(like)) | (Product.category.ilike(like))
        )

    sort_map = {
        'name':  Product.name,
        'stock': Product.current_stock,
        'cost':  Product.unit_cost,
    }
    q = q.order_by(sort_map.get(sort, Product.name))

    paginated = q.paginate(page=page, per_page=limit, error_out=False)

    return _ok(
        [p.to_dict() for p in paginated.items],
        pagination={
            'page':       paginated.page,
            'limit':      limit,
            'total':      paginated.total,
            'pages':      paginated.pages,
            'has_next':   paginated.has_next,
            'has_prev':   paginated.has_prev,
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sales
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/sales', methods=['GET'])
@jwt_required()
def sales():
    """
    Recent sales with optional date filter.

    Query params:
        page        (int, default 1)
        limit       (int, default 20, max 100)
        from_date   (ISO date string, e.g. 2025-01-01)
        to_date     (ISO date string)
        product_id  (int) — filter by product
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    page       = max(1, request.args.get('page',  1,  type=int))
    limit      = min(100, max(1, request.args.get('limit', 20, type=int)))
    from_date  = request.args.get('from_date')
    to_date    = request.args.get('to_date')
    product_id = request.args.get('product_id', type=int)

    q = Sale.query.order_by(desc(Sale.sale_date))

    if from_date:
        try:
            q = q.filter(Sale.sale_date >= datetime.fromisoformat(from_date))
        except ValueError:
            return _error('from_date must be ISO format (YYYY-MM-DD)')

    if to_date:
        try:
            end = datetime.fromisoformat(to_date) + timedelta(days=1)
            q = q.filter(Sale.sale_date < end)
        except ValueError:
            return _error('to_date must be ISO format (YYYY-MM-DD)')

    if product_id:
        q = q.filter(Sale.product_id == product_id)

    paginated = q.paginate(page=page, per_page=limit, error_out=False)

    return _ok(
        [s.to_dict() for s in paginated.items],
        pagination={
            'page':     paginated.page,
            'limit':    limit,
            'total':    paginated.total,
            'pages':    paginated.pages,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# Alerts
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/alerts', methods=['GET'])
@jwt_required()
def alerts():
    """
    Inventory / stock alerts.

    Query params:
        active_only  (bool, default true)
        severity     (str) — "CRITICAL" | "WARNING" | "INFO"
        limit        (int, default 50)
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    active_only = request.args.get('active_only', 'true').lower() != 'false'
    severity    = request.args.get('severity')
    limit       = min(200, max(1, request.args.get('limit', 50, type=int)))

    q = Alert.query.order_by(desc(Alert.created_at))

    if active_only:
        q = q.filter_by(is_active=True, is_acknowledged=False)

    if severity:
        q = q.filter_by(severity=severity.upper())

    items = q.limit(limit).all()
    return _ok([a.to_dict() for a in items], total=len(items))


# ══════════════════════════════════════════════════════════════════════════════
# Forecasts
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/forecasts', methods=['GET'])
@jwt_required()
def forecasts():
    """
    Sales forecasts for a product (or all products).

    Query params:
        product_id        (int) — omit to get all products
        aggregation_level (str) — "daily" | "weekly" | "monthly"  (default: daily)
        limit             (int, default 14)
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    product_id        = request.args.get('product_id', type=int)
    aggregation_level = request.args.get('aggregation_level', 'daily')
    limit             = min(90, max(1, request.args.get('limit', 14, type=int)))

    q = Forecast.query.filter_by(aggregation_level=aggregation_level) \
                      .order_by(Forecast.forecast_date)

    if product_id:
        q = q.filter_by(product_id=product_id)

    items = q.limit(limit).all()
    return _ok([f.to_dict() for f in items], total=len(items))


# ══════════════════════════════════════════════════════════════════════════════
# Batches (expiration tracking)
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/batches', methods=['GET'])
@jwt_required()
def batches():
    """
    Inventory batches — useful for expiry monitoring on mobile.

    Query params:
        product_id    (int)
        urgency       (str) — "CRITICAL" | "HIGH" | "MEDIUM" | "OK" | "EXPIRED"
        limit         (int, default 30)
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    product_id = request.args.get('product_id', type=int)
    urgency    = (request.args.get('urgency') or '').upper()
    limit      = min(200, max(1, request.args.get('limit', 30, type=int)))

    q = InventoryBatch.query.filter(InventoryBatch.quantity > 0) \
                            .order_by(InventoryBatch.expiration_date)

    if product_id:
        q = q.filter_by(product_id=product_id)

    items = q.limit(limit).all()

    # Apply urgency filter in Python (computed property)
    if urgency:
        items = [b for b in items if b.urgency_level() == urgency]

    return _ok([b.to_dict() for b in items], total=len(items))
