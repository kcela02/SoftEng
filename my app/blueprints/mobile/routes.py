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
from models import db, User, Product, Sale, Alert, Forecast, InventoryBatch, ImportLog
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from . import mobile_bp


# ─────────────────────────────────────────────────────── helpers ────────────

def _current_user():
    """Return the User object whose id is stored in the JWT."""
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


def _error(message, status=400):
    return jsonify({'success': False, 'error': message}), status


def _ok(data=None, **kwargs):
    payload = {'success': True}
    if data is not None:
        payload['data'] = data
    payload.update(kwargs)
    return jsonify(payload), 200


# ══════════════════════════════════════════════════════════════════════════════
# Health / wake-up endpoint  (no auth required)
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/ping', methods=['GET'])
def ping():
    """
    Lightweight endpoint used by the Android app to warm up the Render dyno
    as soon as the login screen is shown.  No DB query — instant response.
    """
    return jsonify({'ok': True}), 200


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

    access_token  = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'success': True,
        'access_token':  access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
    }), 200


@mobile_bp.route('/auth/register', methods=['POST'])
def mobile_register():
    """
    Register a new user account (no JWT required).

    Request body (JSON):
        { "username": "...", "email": "...", "password": "..." }

    Password rules mirror server config:
        PASSWORD_MIN_LENGTH = 8, REQUIRE_UPPERCASE, REQUIRE_LOWERCASE, REQUIRE_NUMBERS

    Role assignment:
        - First user ever → admin (owner/bootstrap)
        - All others     → user  (promote via web dashboard)
    """
    data = request.get_json(silent=True)
    if not data:
        return _error('Request body must be JSON')

    username = (data.get('username') or '').strip()
    email    = (data.get('email')    or '').strip()
    password =  data.get('password') or ''

    if not username or not email or not password:
        return _error('username, email and password are required')

    if User.query.filter_by(username=username).first():
        return _error('Username already taken', 409)

    if User.query.filter_by(email=email).first():
        return _error('Email already registered', 409)

    is_valid, error_msg = User.validate_password_strength(password)
    if not is_valid:
        return _error(error_msg, 400)

    # First registered user becomes admin/owner (bootstrap case)
    is_first = db.session.query(User).count() == 0
    role     = 'admin' if is_first else 'user'

    user = User(username=username, email=email, role=role, is_owner=is_first)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return _ok(
        {'id': user.id, 'username': user.username, 'role': user.role},
        message='Registration successful'
    )


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
    return _ok(access_token=create_access_token(identity=str(user.id)))


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
                        .filter(Sale.sale_date >= dt,
                                Sale.is_fake == False).scalar()
        return round(float(row or 0), 2)

    total_products  = Product.query.filter_by(is_fake=False).count()
    low_stock_count = Product.query.filter(
        Product.is_fake == False,
        Product.current_stock <= 10
    ).count()

    active_alerts = Alert.query.filter_by(
        is_active=True, is_acknowledged=False
    ).count()

    # Alert breakdown by severity
    alerts_critical = Alert.query.filter_by(
        is_active=True, is_acknowledged=False, severity='CRITICAL'
    ).count()
    alerts_warning = Alert.query.filter_by(
        is_active=True, is_acknowledged=False, severity='WARNING'
    ).count()
    alerts_info = Alert.query.filter_by(
        is_active=True, is_acknowledged=False, severity='INFO'
    ).count()

    # Total inventory value: sum(current_stock * unit_cost) for real products
    inv_val_row = db.session.query(
        func.sum(Product.current_stock * Product.unit_cost)
    ).filter(Product.is_fake == False).scalar()
    inventory_value = round(float(inv_val_row or 0), 2)

    # Batches expiring within the next 7 days
    today = now.date()
    seven_days_later = today + timedelta(days=7)
    expiring_soon = InventoryBatch.query.filter(
        InventoryBatch.expiration_date >= today,
        InventoryBatch.expiration_date <= seven_days_later,
        InventoryBatch.quantity > 0
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
        .filter(Sale.sale_date >= thirty_days_ago,
                Sale.is_fake == False,
                Product.is_fake == False)
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
        'alerts_by_severity': {
            'critical': alerts_critical,
            'warning':  alerts_warning,
            'info':     alerts_info,
        },
        'inventory_value': inventory_value,
        'expiring_soon':  expiring_soon,
        'top_products':   top_products,
        'generated_at':   now.isoformat(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# Sales chart data  (pre-aggregated daily + monthly totals for the mobile chart)
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/sales/chart', methods=['GET'])
@jwt_required()
def sales_chart():
    """
    Returns pre-aggregated daily and monthly revenue/quantity totals for a date
    range.  One database query — no pagination needed.

    Query params:
        from_date  (ISO date, e.g. 2025-01-01)   default: 90 days ago
        to_date    (ISO date)                     default: today
        product_id (int, optional)

    Response:
        {
          "success": true,
          "data": {
            "daily":   [ {"date":"2025-01-01","revenue":1234.5,"quantity":20}, ... ],
            "monthly": [ {"month":"2025-01", "revenue":12345.0,"quantity":200}, ... ],
            "total_revenue": 123456.0,
            "total_quantity": 2000
          }
        }
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    from sqlalchemy import cast, Date as SADate

    now        = datetime.utcnow()
    default_from = (now - timedelta(days=90)).date()
    default_to   = now.date()

    from_date_str = request.args.get('from_date')
    to_date_str   = request.args.get('to_date')
    product_id    = request.args.get('product_id', type=int)

    try:
        from_dt = datetime.fromisoformat(from_date_str) if from_date_str else datetime.combine(default_from, datetime.min.time())
        to_dt   = datetime.fromisoformat(to_date_str)   + timedelta(days=1) if to_date_str else datetime.combine(default_to, datetime.min.time()) + timedelta(days=1)
    except ValueError:
        return _error('from_date / to_date must be ISO format (YYYY-MM-DD)')

    # Cast datetime → date so we can GROUP BY calendar day
    sale_day_expr = cast(Sale.sale_date, SADate)

    q = db.session.query(
        sale_day_expr.label('sale_day'),
        func.sum(Sale.quantity * Sale.price).label('revenue'),
        func.sum(Sale.quantity).label('quantity')
    ).filter(
        Sale.sale_date >= from_dt,
        Sale.sale_date < to_dt,
        Sale.is_fake == False
    )

    if product_id:
        q = q.filter(Sale.product_id == product_id)

    daily_rows = q.group_by(sale_day_expr).order_by(sale_day_expr).all()

    # Build daily list and accumulate monthly
    from collections import defaultdict
    monthly = defaultdict(lambda: {'revenue': 0.0, 'quantity': 0})
    daily   = []
    total_revenue  = 0.0
    total_quantity = 0

    for row in daily_rows:
        d   = str(row.sale_day)          # "YYYY-MM-DD"
        rev = round(float(row.revenue  or 0), 2)
        qty = int(row.quantity or 0)
        daily.append({'date': d, 'revenue': rev, 'quantity': qty})
        month_key = d[:7]                # "YYYY-MM"
        monthly[month_key]['revenue']  += rev
        monthly[month_key]['quantity'] += qty
        total_revenue  += rev
        total_quantity += qty

    monthly_list = [
        {'month': k, 'revenue': round(v['revenue'], 2), 'quantity': v['quantity']}
        for k, v in sorted(monthly.items())
    ]

    return _ok({
        'daily':          daily,
        'monthly':        monthly_list,
        'total_revenue':  round(total_revenue, 2),
        'total_quantity': total_quantity,
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

    # Build a map of product_id → highest active alert severity so the
    # mobile app can display the same classification as the web dashboard.
    product_ids = [p.id for p in paginated.items]
    alert_map = {}
    if product_ids:
        severity_order = {'CRITICAL': 3, 'HIGH': 2, 'MEDIUM': 1}
        active_alerts = Alert.query.filter(
            Alert.product_id.in_(product_ids),
            Alert.is_active == True,
            Alert.is_acknowledged == False,
        ).all()
        for a in active_alerts:
            cur = alert_map.get(a.product_id)
            a_rank = severity_order.get(a.severity, 0)
            if cur is None or a_rank > severity_order.get(cur, 0):
                alert_map[a.product_id] = a.severity

    data = []
    for p in paginated.items:
        d = p.to_dict()
        d['alert_level'] = alert_map.get(p.id)   # None when stock is adequate
        data.append(d)

    return _ok(
        data,
        pagination={
            'page':       paginated.page,
            'limit':      limit,
            'total':      paginated.total,
            'pages':      paginated.pages,
            'has_next':   paginated.has_next,
            'has_prev':   paginated.has_prev,
        }
    )


@mobile_bp.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    """
    Create a new product. Admin / Manager only.

    Request body (JSON):
        {
          "name":          "Blue Razz Ice 50mg",  // required
          "category":      "Disposable",           // optional
          "unit_cost":     5.50,                   // optional, default 0
          "current_stock": 100                     // optional, default 0
        }
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)
    if user.role not in ('admin', 'manager'):
        return _error('Only admins and managers can add products.', 403)

    data = request.get_json(silent=True)
    if not data or not (data.get('name') or '').strip():
        return _error('Product name is required')

    name = data['name'].strip()

    existing = Product.query.filter(
        Product.name.ilike(name),
        Product.is_fake == False
    ).first()
    if existing:
        return _error(f"A product named '{existing.name}' already exists.", 409)

    try:
        product = Product(
            name=name,
            category=(data.get('category') or '').strip() or None,
            unit_cost=float(data.get('unit_cost') or 0),
            current_stock=int(data.get('current_stock') or 0),
        )
        db.session.add(product)
        db.session.commit()
        return _ok(product.to_dict())
    except Exception as e:
        db.session.rollback()
        return _error(f'Could not create product: {str(e)}')


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

    q = Sale.query.filter_by(is_fake=False).order_by(desc(Sale.sale_date))

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
# Forecast Accuracy
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/forecast-accuracy', methods=['GET'])
@jwt_required()
def forecast_accuracy():
    """
    Returns MAPE-based forecast accuracy (0–100 %) using the same calculation
    method as the web dashboard's /api/forecast-accuracy endpoint.

    Query params:
        days_back (int, default 90) — evaluation window in days
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    try:
        from utils.forecast_evaluator import ForecastEvaluator
        days_back = request.args.get('days_back', 90, type=int)
        acc = ForecastEvaluator.calculate_mape(days_back=days_back)
        return _ok({'accuracy': acc})
    except Exception as e:
        return _error(str(e), 500)


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
        from_date         (ISO date string, e.g. 2025-01-01)
        to_date           (ISO date string)
        page              (int, default 1)
        limit             (int, default 100, max 100)
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    product_id        = request.args.get('product_id', type=int)
    aggregation_level = request.args.get('aggregation_level', 'daily')
    from_date         = request.args.get('from_date')
    to_date           = request.args.get('to_date')
    page              = max(1, request.args.get('page', 1, type=int))
    limit             = min(100, max(1, request.args.get('limit', 100, type=int)))

    q = Forecast.query.filter_by(aggregation_level=aggregation_level) \
                      .order_by(Forecast.forecast_date)

    if product_id:
        q = q.filter_by(product_id=product_id)

    if from_date:
        try:
            q = q.filter(Forecast.forecast_date >= datetime.fromisoformat(from_date))
        except ValueError:
            return _error('from_date must be ISO format (YYYY-MM-DD)')

    if to_date:
        try:
            end = datetime.fromisoformat(to_date) + timedelta(days=1)
            q = q.filter(Forecast.forecast_date < end)
        except ValueError:
            return _error('to_date must be ISO format (YYYY-MM-DD)')

    paginated = q.paginate(page=page, per_page=limit, error_out=False)

    return _ok(
        [f.to_dict() for f in paginated.items],
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


# ══════════════════════════════════════════════════════════════════════════════
# Reports — mirrors the web /api/sales-report, /api/inventory-report,
#            /api/list-imports but JWT-protected for mobile.
# ══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route('/reports/sales', methods=['GET'])
@jwt_required()
def reports_sales():
    """
    Sales report identical to the web dashboard.

    Query params
    ------------
    period : str   — "7d" | "30d" | "90d" | "1y" | "all"  (default "30d")
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    period = request.args.get('period', '30d')
    end_date = datetime.utcnow()

    if period == '7d':
        start_date = end_date - timedelta(days=7)
        period_label = 'Last 7 Days'
    elif period == '90d':
        start_date = end_date - timedelta(days=90)
        period_label = 'Last 90 Days'
    elif period == '1y':
        start_date = end_date - timedelta(days=365)
        period_label = 'This Year'
    elif period == 'all':
        start_date = datetime(2000, 1, 1)
        period_label = 'All Time'
    else:                       # default / "30d"
        start_date = end_date - timedelta(days=30)
        period_label = 'Last 30 Days'

    rows = db.session.query(
        Sale.sale_date,
        Product.name.label('product_name'),
        Sale.quantity,
        Sale.price,
        (Sale.quantity * Sale.price).label('revenue')
    ).join(Product, Sale.product_id == Product.id).filter(
        Sale.sale_date >= start_date,
        Sale.sale_date <= end_date
    ).order_by(Sale.sale_date.desc()).all()

    sales_data = []
    total_revenue = 0.0
    for r in rows:
        rev = float(r.quantity * r.price)
        sales_data.append({
            'date':         r.sale_date.strftime('%Y-%m-%d'),
            'product_name': r.product_name,
            'quantity':     r.quantity,
            'price':        float(r.price),
            'revenue':      rev,
        })
        total_revenue += rev

    return _ok({
        'period':        period,
        'period_label':  period_label,
        'sales':         sales_data,
        'total_sales':   len(sales_data),
        'total_revenue': round(total_revenue, 2),
    })


@mobile_bp.route('/reports/inventory', methods=['GET'])
@jwt_required()
def reports_inventory():
    """
    Inventory report identical to the web dashboard.

    Query params
    ------------
    type : str   — "current" | "low" | "all"  (default "current")
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    report_type = request.args.get('type', 'current')

    q = db.session.query(
        Product.id,
        Product.name.label('product_name'),
        Product.category,
        Product.current_stock,
        Product.unit_cost
    ).filter(Product.is_fake == False)

    if report_type == 'low':
        q = q.filter(Product.current_stock <= 50)
        report_label = 'Low Stock Items'
    elif report_type == 'current':
        q = q.filter(Product.current_stock > 0)
        report_label = 'Current Stock Levels'
    else:
        report_label = 'All Inventory'

    q = q.order_by(Product.current_stock.asc())
    items = q.all()

    inventory_data = []
    total_value = 0.0
    for it in items:
        uc = float(it.unit_cost) if it.unit_cost else 0.0
        val = it.current_stock * uc
        inventory_data.append({
            'product_name':  it.product_name,
            'category':      it.category,
            'current_stock': it.current_stock,
            'unit_cost':     uc,
            'total_value':   val,
        })
        total_value += val

    return _ok({
        'report_type':  report_type,
        'report_label': report_label,
        'inventory':    inventory_data,
        'total_items':  len(inventory_data),
        'total_value':  round(total_value, 2),
    })


@mobile_bp.route('/reports/imports', methods=['GET'])
@jwt_required()
def reports_imports():
    """
    Import history identical to the web dashboard.

    Query params
    ------------
    limit : str   — "10" | "25" | "50" | "all"  (default "10")
    """
    user = _current_user()
    if not user:
        return _error('User not found', 401)

    limit_param = request.args.get('limit', '10')
    q = ImportLog.query.order_by(ImportLog.upload_date.desc())

    if limit_param != 'all':
        try:
            lim = int(limit_param)
            q = q.limit(lim)
        except ValueError:
            q = q.limit(10)

    logs = q.all()
    import_list = []
    for imp in logs:
        imp_user = db.session.get(User, imp.user_id) if imp.user_id else None
        import_list.append({
            'id':             imp.id,
            'filename':       imp.filename,
            'upload_date':    imp.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
            'rows_processed': imp.rows_processed,
            'rows_failed':    imp.rows_failed,
            'rows_skipped':   imp.rows_skipped or 0,
            'status':         imp.status,
            'data_type':      imp.data_type,
            'username':       imp_user.username if imp_user else 'Unknown',
        })

    return _ok({
        'imports': import_list,
        'total':   len(import_list),
    })
