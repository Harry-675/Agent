#!/usr/bin/env python3
"""Test infrastructure connectivity - database and cache."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_database_connection():
    """Test database connection."""
    print("🔍 Testing database connection...")
    try:
        from src.database.connection import get_db
        from sqlalchemy import text
        
        db = get_db()
        async with db.session() as session:
            # Test basic query
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            
            if value == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed: unexpected result")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_database_tables():
    """Test if database tables exist."""
    print("\n🔍 Testing database tables...")
    try:
        from src.database.connection import get_db
        from sqlalchemy import text
        
        db = get_db()
        async with db.session() as session:
            # Check if tables exist
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['news_sources', 'news_items', 'processing_logs', 'system_metrics']
            
            print(f"   Found tables: {tables}")
            
            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                print(f"⚠️  Missing tables: {missing_tables}")
                print("   Run database initialization to create tables")
                return False
            else:
                print("✅ All required tables exist")
                return True
                
    except Exception as e:
        print(f"❌ Failed to check tables: {e}")
        return False


async def test_redis_connection():
    """Test Redis connection."""
    print("\n🔍 Testing Redis connection...")
    try:
        from src.cache.connection import get_redis
        
        redis = await get_redis()
        
        # Test basic operations
        await redis.set("test_key", "test_value")
        value = await redis.get("test_key")
        await redis.delete("test_key")
        
        if value == "test_value":
            print("✅ Redis connection successful")
            return True
        else:
            print("❌ Redis connection failed: unexpected result")
            return False
            
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def main():
    """Run all infrastructure tests."""
    print("=" * 60)
    print("🧪 Infrastructure Connectivity Test")
    print("=" * 60)
    
    results = []
    
    # Test database connection
    db_conn = await test_database_connection()
    results.append(("Database Connection", db_conn))
    
    # Test database tables (only if connection works)
    if db_conn:
        db_tables = await test_database_tables()
        results.append(("Database Tables", db_tables))
    else:
        results.append(("Database Tables", None))
    
    # Test Redis connection
    redis_conn = await test_redis_connection()
    results.append(("Redis Connection", redis_conn))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{status} - {name}")
    
    # Overall result
    print("\n" + "=" * 60)
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    total = len(results)
    
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped out of {total}")
    
    if failed > 0:
        print("\n⚠️  Some infrastructure components are not available.")
        print("   This is expected if Docker containers are not running.")
        print("\n💡 To start the infrastructure:")
        print("   1. Install Docker Desktop")
        print("   2. Run: docker-compose up -d")
        print("   3. Wait for containers to be healthy")
        print("   4. Run this test again")
        return 1
    elif skipped > 0:
        print("\n⚠️  Some tests were skipped due to connection failures.")
        return 1
    else:
        print("\n🎉 All infrastructure components are working!")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
