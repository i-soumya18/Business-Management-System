import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_enums():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5433/bms_db')
    
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
        enums = [r[0] for r in result]
        print("Existing enum types:")
        for enum in enums:
            print(f"  - {enum}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_enums())
