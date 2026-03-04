"""
Database initialization script.
Creates all tables and indexes defined in schema.sql.
"""

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_database_url


def init_database():
    """Initialize the database by executing the schema.sql file."""
    schema_path = Path(__file__).parent / "schema.sql"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    # Read the schema SQL
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Connect to database
    db_url = get_database_url()
    print(f"Connecting to database...")
    
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Executing schema creation...")
        cursor.execute(schema_sql)
        
        print("✓ Database schema created successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Verify indexes were created
        cursor.execute("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        
        indexes = cursor.fetchall()
        print(f"\nCreated indexes: {len(indexes)} total")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def drop_all_tables():
    """Drop all tables (use with caution!)."""
    db_url = get_database_url()
    
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Dropping all tables...")
        
        # Drop tables in reverse order to handle foreign key constraints
        tables = ['system_metrics', 'processing_logs', 'news_items', 'news_sources']
        
        for table in tables:
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table)
            ))
            print(f"  - Dropped {table}")
        
        # Drop the trigger function
        cursor.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
        print("  - Dropped trigger function")
        
        cursor.close()
        conn.close()
        
        print("✓ All tables dropped successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize or reset the database")
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Drop all tables before creating (WARNING: destroys all data)'
    )
    
    args = parser.parse_args()
    
    if args.reset:
        print("=" * 60)
        print("WARNING: This will delete all data in the database!")
        print("=" * 60)
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
        
        if not drop_all_tables():
            sys.exit(1)
        print()
    
    if not init_database():
        sys.exit(1)
