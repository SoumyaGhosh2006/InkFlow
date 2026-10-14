"""
InkFlow Core Database Module.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module provides an asynchronous MongoDB connection layer using `motor`, the
official async driver built on top of `PyMongo` and Python's `asyncio` event loop.

Key Capabilities:
1. Lifecycle-managed client singleton: Reuses connection pools across async requests.
2. Index Initialization: Ensures critical unique constraints (e.g., user email)
   and query indexes (e.g., user_id on genomes and rewrite logs) are present upon startup.
3. Collection accessors: Clean dependency-injectable accessors for collections.
================================================================================
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("inkflow.database")


class MongoManager:
    """
    Manages the lifecycle of the AsyncIOMotorClient and database access.
    
    Attributes:
        client: Active AsyncIOMotorClient instance.
        db: Active AsyncIOMotorDatabase reference.
    """

    def __init__(self) -> None:
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None


# Module-level singleton instance holding client references
mongo_manager = MongoManager()


async def connect_to_mongo() -> None:
    """
    Initializes the MongoDB connection pool and creates indexes.
    
    This function is executed during FastAPI's application startup lifespan.
    It establishes the TCP socket pool to the database, verifies connectivity,
    and idempotently builds required unique and query indexes.
    """
    logger.info("Initializing Motor connection to MongoDB: %s", settings.MONGODB_URI)
    try:
        # Create asynchronous client with connection pool configuration
        mongo_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=50,
            minPoolSize=5,
            serverSelectionTimeoutMS=5000,
        )
        mongo_manager.db = mongo_manager.client[settings.MONGODB_DB_NAME]

        # Verify connectivity using the ping command
        await mongo_manager.db.command("ping")
        logger.info("Successfully established connection to MongoDB database: %s", settings.MONGODB_DB_NAME)

        # Idempotently build required database indexes
        await _init_db_indexes(mongo_manager.db)

    except Exception as exc:
        logger.error("Failed to connect to MongoDB during startup: %s", exc, exc_info=True)
        # We do not crash startup here to allow testing/mocked environments to initialize gracefully
        pass


async def close_mongo_connection() -> None:
    """
    Closes all active MongoDB connection pools.
    
    Invoked during FastAPI application shutdown to gracefully release socket descriptors.
    """
    logger.info("Closing Motor MongoDB connection pool...")
    if mongo_manager.client:
        mongo_manager.client.close()
        mongo_manager.client = None
        mongo_manager.db = None
        logger.info("MongoDB connection closed cleanly.")


async def _init_db_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Idempotently creates required indexes across collections.
    
    Indexes established:
    - users: Unique index on 'email' to prevent duplicate account registration.
    - genomes: Unique index on 'user_id' so each user has exactly one Style Genome.
    - rewrites: Descending index on 'user_id' and 'created_at' for fast timeline pagination.
    - drills: Index on 'user_id' and 'completed_at'.
    
    Args:
        db: The active motor database instance.
    """
    try:
        # Index 1: Unique email constraint on users
        await db["users"].create_index("email", unique=True)
        
        # Index 2: Fast lookup for user genome
        await db["genomes"].create_index("user_id", unique=True)

        # Index 3: Compound index for pagination on rewrite history
        await db["rewrites"].create_index([("user_id", 1), ("created_at", -1)])

        # Index 4: Index for drill sessions
        await db["drills"].create_index("user_id")

        logger.info("All collection indexes verified and built successfully.")
    except Exception as exc:
        logger.warning("Index creation notice: %s", exc)


def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency returning the active database reference.
    
    Returns:
        AsyncIOMotorDatabase instance.
    
    Raises:
        RuntimeError: If database connection has not been initialized.
    """
    if mongo_manager.db is None:
        raise RuntimeError("MongoDB connection is not initialized. Ensure startup lifespan has completed.")
    return mongo_manager.db


def get_users_collection():
    """Returns the 'users' MongoDB collection."""
    return get_db()["users"]


def get_genomes_collection():
    """Returns the 'genomes' MongoDB collection."""
    return get_db()["genomes"]


def get_rewrites_collection():
    """Returns the 'rewrites' MongoDB collection."""
    return get_db()["rewrites"]


def get_drills_collection():
    """Returns the 'drills' MongoDB collection."""
    return get_db()["drills"]


def get_sessions_collection():
    """Returns the 'sessions' MongoDB collection."""
    return get_db()["sessions"]
