import asyncio
from database.connect import init_db_pool, acquire_conn

async def main():
    await init_db_pool()
    async with acquire_conn() as conn:
        print("ns_out:")
        cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'ns_out'")
        print([c['column_name'] for c in cols])
        print("main_out:")
        cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'main_out'")
        print([c['column_name'] for c in cols])
        print("ut_out:")
        cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'ut_out'")
        print([c['column_name'] for c in cols])
        
asyncio.run(main())
