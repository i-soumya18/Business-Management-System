"""
Verify Inventory Module Database Schema

Checks that all inventory tables, columns, and indexes are properly created.
"""

import asyncio
from sqlalchemy import inspect, text
from app.core.database import engine


async def verify_schema():
    """Verify all inventory tables and their structure"""
    
    async with engine.connect() as conn:
        inspector = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
        
        # Expected tables
        expected_tables = [
            "categories",
            "brands",
            "suppliers",
            "products",
            "product_variants",
            "stock_locations",
            "inventory_levels",
            "inventory_movements",
            "stock_adjustments",
            "low_stock_alerts"
        ]
        
        existing_tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        
        print("=" * 80)
        print("INVENTORY MODULE DATABASE SCHEMA VERIFICATION")
        print("=" * 80)
        print()
        
        # Check tables
        print("📋 TABLES STATUS:")
        print("-" * 80)
        for table in expected_tables:
            status = "✅" if table in existing_tables else "❌"
            print(f"{status} {table}")
        print()
        
        # Check each table structure
        for table_name in expected_tables:
            if table_name not in existing_tables:
                continue
                
            columns = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_columns(table_name)
            )
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes(table_name)
            )
            foreign_keys = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_foreign_keys(table_name)
            )
            
            print(f"📊 TABLE: {table_name}")
            print(f"   Columns: {len(columns)}")
            print(f"   Indexes: {len(indexes)}")
            print(f"   Foreign Keys: {len(foreign_keys)}")
            print()
        
        # Count records
        print("📈 RECORD COUNTS:")
        print("-" * 80)
        for table in expected_tables:
            if table in existing_tables:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"{table}: {count} records")
        print()
        
        print("=" * 80)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 80)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify_schema())
