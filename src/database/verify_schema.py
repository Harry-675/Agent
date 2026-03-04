"""
Verify database schema is correctly created.
"""

import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_database_url


def verify_schema():
    """Verify that all expected tables and indexes exist."""
    db_url = get_database_url()
    
    expected_tables = ['news_sources', 'news_items', 'processing_logs', 'system_metrics']
    expected_indexes = [
        'idx_news_sources_enabled',
        'idx_news_sources_name',
        'idx_news_items_published_at',
        'idx_news_items_categories',
        'idx_news_items_duplicate_group',
        'idx_news_items_created_at',
        'idx_news_items_url',
        'idx_processing_logs_news_id',
        'idx_processing_logs_created_at',
        'idx_processing_logs_stage_status',
        'idx_system_metrics_type_time',
        'idx_system_metrics_recorded_at',
    ]
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("Verifying database schema...")
        print("=" * 60)
        
        # Check tables
        print("\n1. Checking tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_tables_ok = True
        for table in expected_tables:
            if table in existing_tables:
                print(f"   ✓ {table}")
            else:
                print(f"   ✗ {table} (MISSING)")
                all_tables_ok = False
        
        # Check indexes
        print("\n2. Checking indexes...")
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY indexname;
        """)
        
        existing_indexes = [row[0] for row in cursor.fetchall()]
        
        all_indexes_ok = True
        for index in expected_indexes:
            if index in existing_indexes:
                print(f"   ✓ {index}")
            else:
                print(f"   ✗ {index} (MISSING)")
                all_indexes_ok = False
        
        # Check triggers
        print("\n3. Checking triggers...")
        cursor.execute("""
            SELECT trigger_name, event_object_table
            FROM information_schema.triggers
            WHERE trigger_schema = 'public'
            ORDER BY event_object_table, trigger_name;
        """)
        
        triggers = cursor.fetchall()
        if triggers:
            for trigger_name, table_name in triggers:
                print(f"   ✓ {trigger_name} on {table_name}")
        else:
            print("   ⚠ No triggers found")
        
        # Check functions
        print("\n4. Checking functions...")
        cursor.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name;
        """)
        
        functions = cursor.fetchall()
        if functions:
            for func in functions:
                print(f"   ✓ {func[0]}")
        else:
            print("   ⚠ No functions found")
        
        # Summary
        print("\n" + "=" * 60)
        if all_tables_ok and all_indexes_ok:
            print("✓ Schema verification PASSED")
            print("All expected tables and indexes are present.")
            return True
        else:
            print("✗ Schema verification FAILED")
            if not all_tables_ok:
                print("Some tables are missing.")
            if not all_indexes_ok:
                print("Some indexes are missing.")
            return False
        
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    success = verify_schema()
    sys.exit(0 if success else 1)
