import asyncio
import asyncpg

async def check_schema():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/bitinglip_tasks')
    columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='tasks' 
        ORDER BY ordinal_position
    """)
    print("Tasks table columns:")
    for col in columns:
        print(f"  - {col['column_name']}: {col['data_type']}")
    await conn.close()

asyncio.run(check_schema())
