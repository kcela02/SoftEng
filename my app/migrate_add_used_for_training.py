"""
Database Migration Script
Adds the missing 'used_for_training' column to the sale table
Run this script to fix the database schema
"""
from app import create_app, db
from sqlalchemy import text


def migrate_sale_table():
    app = create_app()
    
    with app.app_context():
        # Check current database type
        engine = db.engine
        db_type = engine.dialect.name
        print(f"Detected database: {db_type}")
        
        try:
            # Try to add the column
            if db_type == 'postgresql':
                # PostgreSQL syntax
                db.session.execute(text("""
                    ALTER TABLE sale 
                    ADD COLUMN IF NOT EXISTS used_for_training BOOLEAN DEFAULT 0
                """))
            else:
                # SQLite and others
                # First check if column exists
                result = db.session.execute(text("PRAGMA table_info(sale)"))
                columns = [row[1] for row in result]
                
                if 'used_for_training' not in columns:
                    db.session.execute(text(
                        "ALTER TABLE sale ADD COLUMN used_for_training BOOLEAN DEFAULT 0"
                    ))
                    print("Column 'used_for_training' added successfully!")
                else:
                    print("Column 'used_for_training' already exists.")
            
            db.session.commit()
            print(f"[OK] Database migration completed for {db_type}!")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Migration failed: {e}")
            print("\nFor PostgreSQL, try running manually:")
            print("  ALTER TABLE sale ADD COLUMN used_for_training BOOLEAN DEFAULT 0;")


if __name__ == "__main__":
    migrate_sale_table()
