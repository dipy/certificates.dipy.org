#!/usr/bin/env python3
"""
Standalone script to initialize the database manually.
Run this if you encounter database initialization issues.
"""

import asyncio
from database import init_db


async def main():
    print("Initializing database...")
    try:
        await init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())