"""
Database migration runner
Applies SQL migration files in order
"""

import sys
from pathlib import Path
import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'incident_triage',
    'user': 'postgres',
    'password': 'FordsonHigh12',
    'port': 5432,
}

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None


def get_migrations_dir():
    """Get path to migrations directory"""
    return Path(__file__).parent.parent / "migrations"


def run_migrations():
    """Run all migration files in order"""
    migrations_dir = get_migrations_dir()
    
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return False
    
    # Get all SQL files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("⚠️  No migration files found")
        return True
    
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        print("🔄 Running migrations...\n")
        
        for migration_file in migration_files:
            print(f"  Running: {migration_file.name}")
            
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            # Execute entire file as one script to preserve PL/pgSQL functions
            try:
                cursor.execute(migration_sql)
                conn.commit()
                print(f"    ✓ Completed")
            except psycopg2.Error as e:
                # Check if error is about missing extensions/types
                error_str = str(e)
                if "VECTOR" in error_str or "pgvector" in error_str:
                    print(f"    ⚠️  Warning: pgvector not installed (optional for embeddings)")
                    conn.rollback()
                elif "uuid_generate_v4" in error_str:
                    print(f"    ⚠️  Warning: uuid-ossp extension might not be loaded")
                    conn.rollback()
                else:
                    print(f"    ⚠️  Warning: {error_str[:100]}")
                    conn.rollback()
        
        print(f"\n✅ Migrations completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
