"""Check existing database tables"""
import asyncio
from sqlalchemy import inspect
from app.core.database import engine


async def check_tables():
    async with engine.connect() as conn:
        result = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        print("Existing tables in database:")
        for table in sorted(result):
            print(f"  - {table}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_tables())
