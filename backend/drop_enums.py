import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def drop_enums():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5433/bms_db')
    
    async with engine.begin() as conn:
        await conn.execute(text('DROP TYPE IF EXISTS orderhistoryaction CASCADE'))
        await conn.execute(text('DROP TYPE IF EXISTS fulfillmentstatus CASCADE'))
        print('Enums dropped successfully')
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(drop_enums())
