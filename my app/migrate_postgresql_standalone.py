"""
Standalone PostgreSQL Migration Script
Run this to fix database schema issues on Render
Usage: python migrate_postgresql_standalone.py
"""
import os
import sys

# Set up Flask environment
os.environ.setdefault('FLASK_ENV', 'production')

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from sqlalchemy import text, inspect


def migrate_postgresql():
    """Run comprehensive migration for PostgreSQL database."""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("PostgreSQL Database Migration")
        print("=" * 60)
        
        # Check database type
        engine = db.engine
        db_type = engine.dialect.name
        print(f"\nDatabase type: {db_type}")
        
        if db_type != 'postgresql':
            print(f"WARNING: Expected PostgreSQL but got {db_type}")
            print("This script is designed for PostgreSQL.")
            return
        
        # Get inspector to check existing columns
        inspector = inspect(engine)
        
        # Tables to check and their columns
        # Format: (table_name, column_name, column_definition)
        migrations = [
            # Sale table
            ('sale', 'used_for_training', 'BOOLEAN DEFAULT FALSE'),
            
            # Add more columns here as needed
        ]
        
        for table_name, column_name, column_def in migrations:
            print(f"\nChecking {table_name}.{column_name}...")
            
            try:
                # Check if column exists
                columns = inspector.get_columns(table_name)
                column_names = [col['name'] for col in columns]
                
                if column_name in column_names:
                    print(f"  ✓ Column '{column_name}' already exists")
                else:
                    # Add column
                    print(f"  → Adding column '{column_name}'...")
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"  ✓ Added column '{column_name}'")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                db.session.rollback()
        
        # Verify all columns exist
        print("\n" + "=" * 60)
        print("Verification - Current schema:")
        print("=" * 60)
        
        for table_name, column_name, _ in migrations:
            try:
                columns = inspector.get_columns(table_name)
                column_names = [col['name'] for col in columns]
                status = "✓ EXISTS" if column_name in column_names else "✗ MISSING"
                print(f"  {table_name}.{column_name}: {status}")
            except Exception as e:
                print(f"  {table_name}: Error checking - {e}")
        
        print("\n" + "=" * 60)
        print("Migration complete!")
        print("=" * 60)


if __name__ == "__main__":
    migrate_postgresql()
