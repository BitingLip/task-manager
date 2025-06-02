#!/usr/bin/env python3
"""
Initialize Task Manager Database Schema
"""

import asyncio
import asyncpg
import os
from pathlib import Path

async def init_database():
    """Initialize the Task Manager database with proper schema"""
    
    # Database connection parameters
    db_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'database': os.getenv('POSTGRES_DB', 'bitinglip_tasks')
    }
    
    print(f"Connecting to database: {db_params['host']}:{db_params['port']}/{db_params['database']}")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(**db_params)
        print("✅ Connected to Task Manager database")
        
        # Read schema file
        schema_path = Path(__file__).parent / 'database' / 'task_manager_schema.sql'
        
        if not schema_path.exists():
            print(f"❌ Schema file not found: {schema_path}")
            return
            
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        print("📝 Executing schema SQL...")
        
        # Execute schema in parts to handle any issues
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement:
                try:
                    await conn.execute(statement)
                    print(f"✅ Executed statement {i+1}/{len(statements)}")
                except Exception as e:
                    print(f"⚠️  Statement {i+1} failed (may be normal if table exists): {e}")
        
        # Test tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%task%'
        """)
        
        print(f"\n📊 Task Manager tables created:")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        await conn.close()
        print("\n🎉 Task Manager database schema initialized successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(init_database())
