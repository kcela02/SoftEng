"""
migrate_to_render.py
--------------------
Wipes the Render PostgreSQL database and copies ALL local SQLite data to it 1:1.
Run once from the project root:
    python migrate_to_render.py
"""

import sqlite3
import os
import sys

# -- Config ------------------------------------------------------------------
SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
PG_URL      = (
    "postgresql://softeng:TJJwyF4gLQPlQrZNdEh90UVkZG4lC45C"
    "@dpg-d628qm0gjchc73ag8t3g-a.singapore-postgres.render.com/softeng"
)

# Tables in dependency order (parents before children) for INSERT,
# reverse order used for DROP.
TABLE_ORDER = [
    'user',
    'product',
    'sale',
    'inventory',
    'inventory_batches',
    'batch_transactions',
    'log',
    'import_log',
    'forecast',
    'user_preferences',
    'alerts',
    'dashboard_metrics',
    'websocket_sessions',
    'forecast_snapshots',
]

# -- Helpers ------------------------------------------------------------------
def coerce(value):
    """Convert SQLite types to PostgreSQL-compatible Python types."""
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return value


def migrate():
    # -- 1. Verify SQLite file exists -----------------------------------------
    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)

    # -- 2. Drop all remote tables then recreate via SQLAlchemy ---------------
    print("Step 1/4 -- Dropping old remote tables and recreating schema...")
    os.environ['DATABASE_URL'] = PG_URL
    sys.path.insert(0, os.path.dirname(__file__))

    import psycopg2          # imported early so drop step can run
    import psycopg2.extras

    # Drop in reverse FK order using raw psycopg2 (avoids app-startup queries)
    _drop_conn = psycopg2.connect(PG_URL, sslmode='require')
    _drop_conn.autocommit = True
    _drop_cur = _drop_conn.cursor()
    for _t in reversed(TABLE_ORDER):
        _drop_cur.execute(f'DROP TABLE IF EXISTS "{_t}" CASCADE;')
        print(f"          Dropped (if existed): {_t}")
    _drop_cur.close()
    _drop_conn.close()

    # Now recreate all tables cleanly using a minimal Flask app
    # (avoids create_app()'s startup admin-user query on stale schema)
    from flask import Flask
    from models import db as flask_db
    import models  # ensure all model classes are registered

    _mini = Flask(__name__)
    _mini.config['SQLALCHEMY_DATABASE_URI'] = PG_URL
    _mini.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'sslmode': 'require'}
    }
    flask_db.init_app(_mini)
    with _mini.app_context():
        flask_db.create_all()
    print("          Fresh schema created on PostgreSQL.")

    # -- 3. Open connections ---------------------------------------------------
    print("Step 2/4 -- Opening database connections...")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    def open_pg():
        conn = psycopg2.connect(PG_URL, sslmode='require',
                                keepalives=1, keepalives_idle=60,
                                keepalives_interval=10, keepalives_count=5)
        conn.autocommit = False
        return conn, conn.cursor()

    pg_conn, pg_cur = open_pg()
    print("          Connected to both databases.")

    # -- 4. Copy each table ----------------------------------------------------
    print("Step 3/4 -- Copying data from SQLite -> PostgreSQL...")

    # Pre-load boolean column names for every table from PostgreSQL's schema
    pg_cur.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND data_type = 'boolean'
    """)
    bool_cols_by_table: dict = {}
    for tname, cname in pg_cur.fetchall():
        bool_cols_by_table.setdefault(tname, set()).add(cname)

    sqlite_cur = sqlite_conn.cursor()
    total_rows = 0

    for table in TABLE_ORDER:
        # Check if table exists in SQLite (some may not yet)
        sqlite_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if not sqlite_cur.fetchone():
            print(f"          Skipped (not in SQLite): {table}")
            continue

        sqlite_cur.execute(f'SELECT * FROM "{table}"')
        rows = sqlite_cur.fetchall()

        if not rows:
            print(f"          Empty (0 rows):  {table}")
            continue

        # Get column names from SQLite cursor description
        cols = [desc[0] for desc in sqlite_cur.description]
        bool_cols = bool_cols_by_table.get(table, set())

        col_list     = ', '.join(f'"{c}"' for c in cols)
        placeholders = ', '.join(['%s'] * len(cols))
        insert_sql   = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

        def coerce_row(row):
            out = []
            for col, val in zip(cols, row):
                if val is None:
                    out.append(None)
                elif col in bool_cols:
                    out.append(bool(val))        # convert 0/1 -> False/True
                elif isinstance(val, bytes):
                    out.append(val.decode('utf-8', errors='replace'))
                else:
                    out.append(val)
            return tuple(out)

        data = [coerce_row(row) for row in rows]

        try:
            # Insert in small chunks so Render doesn't time out the connection
            CHUNK = 100
            for i in range(0, len(data), CHUNK):
                chunk = data[i:i + CHUNK]
                try:
                    psycopg2.extras.execute_batch(pg_cur, insert_sql, chunk, page_size=50)
                    pg_conn.commit()
                except (psycopg2.OperationalError, psycopg2.InterfaceError):
                    # Reconnect and retry this chunk once
                    try:
                        pg_conn.close()
                    except Exception:
                        pass
                    pg_conn, pg_cur = open_pg()
                    psycopg2.extras.execute_batch(pg_cur, insert_sql, chunk, page_size=50)
                    pg_conn.commit()
            print(f"          Copied {len(rows):>6} rows -> {table}")
            total_rows += len(rows)
        except Exception as e:
            try:
                pg_conn.rollback()
            except Exception:
                pass
            print(f"  ERROR copying table '{table}': {e}")
            print("  Continuing with remaining tables...")

    # -- 6. Reset sequences ----------------------------------------------------
    print("\nStep 4/4 -- Resetting PostgreSQL sequences to match max IDs...")
    for table in TABLE_ORDER:
        sqlite_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if not sqlite_cur.fetchone():
            continue
        sqlite_cur.execute(f'SELECT MAX(id) FROM "{table}"')
        row = sqlite_cur.fetchone()
        max_id = row[0] if row and row[0] is not None else 0
        if max_id > 0:
            pg_cur.execute(
                f"SELECT setval(pg_get_serial_sequence('\"{table}\"', 'id'), %s, true);",
                (max_id,)
            )
            print(f"          {table}: sequence -> {max_id}")
    pg_conn.commit()

    # -- Done -----------------------------------------------------------------
    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()

    print(f"\nOK Migration complete. {total_rows} total rows copied to Render PostgreSQL.")
    print("  The remote database is now an exact copy of your local SQLite data.")


if __name__ == '__main__':
    migrate()

