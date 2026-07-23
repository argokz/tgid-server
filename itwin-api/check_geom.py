import asyncio
from database.connect import init_db_pool
from database.db import acquire_conn

async def main():
    await init_db_pool()
    async with acquire_conn() as c:
        # Test ST_SetPoint
        try:
            line = await c.fetchrow("""
                SELECT ST_AsText(shape) as old_wkt, 
                       ST_AsText(ST_SetPoint(shape, 0, ST_MakePoint(0,0))) as new_wkt 
                FROM linesobj WHERE shape IS NOT NULL LIMIT 1
            """)
            print("Line old:", line['old_wkt'])
            print("Line new:", line['new_wkt'])
        except Exception as e:
            print("ST_SetPoint failed:", e)

if __name__ == '__main__':
    asyncio.run(main())
