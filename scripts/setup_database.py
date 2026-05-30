import asyncio
from src.db.session import engine
from src.db.models import Base

async def setup_db() -> None:
    """Creates all database tables defined in models.py using the async engine."""
    print("Initializing database tables...")
    async with engine.begin() as conn:
        # Create all tables defined in Base.metadata
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully!")

def main() -> None:
    """CLI entrypoint for database initialization."""
    asyncio.run(setup_db())

if __name__ == "__main__":
    main()
