"""
Automatic Database Migration Script
Checks and adds missing columns automatically on startup
Run this once or on app startup to ensure all columns exist
"""
from app import create_app, db
from sqlalchemy import text


def auto_migrate():
    """Automatically detect and add missing columns."""
    app = create_app()
    
    with app.app_context():
        # Get database type
        engine = db.engine
        db_type = engine.dialect.name
        print(f"Database: {db_type}")
        
        migrations_applied = []
        
        # List of columns to add: (table_name, column_name, column_definition)
        columns_to_add = [
            ('sale', 'used_for_training', 'BOOLEAN DEFAULT 0'),
        ]
        
        try:
            for table_name, column_name, column_def in columns_to_add:
                try:
                    if db_type == 'postgresql':
                        # PostgreSQL - use IF NOT EXISTS
                        sql = f"""
                            DO $$ 
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM information_schema.columns 
                                    WHERE table_name = '{table_name}' 
                                    AND column_name = '{column_name}'
                                ) THEN
                                    ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};
                                END IF;
                            END $$;
                        """
                    else:
                        # SQLite and others - check first
                        result = db.session.execute(text(f"PRAGMA table_info({table_name})"))
                        columns = [row[1] for row in result]
                        
                        if column_name not in columns:
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                        else:
                            sql = None
                    
                    if sql:
                        db.session.execute(text(sql))
                        db.session.commit()
                        migrations_applied.append(f"  ✓ Added {column_name} to {table_name}")
                        print(f"  ✓ Added {column_name} to {table_name}")
                    else:
                        print(f"  - {column_name} in {table_name} already exists")
                        
                except Exception as e:
                    print(f"  ✗ Error adding {column_name} to {table_name}: {e}")
                    db.session.rollback()
            
            if migrations_applied:
                print(f"\n✓ Migrations applied successfully!")
            else:
                print(f"\n✓ Database schema is up to date!")
                
        except Exception as e:
            print(f"Migration error: {e}")


if __name__ == "__main__":
    auto_migrate()
