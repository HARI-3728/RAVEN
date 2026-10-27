"""Storage Database - SQLite database schema and connection management for RAVEN."""

import sqlite3
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path


class Database:
    """SQLite database schema and connection management for RAVEN."""
    
    def __init__(self, path: str = ":memory:"):
        """Initialize the database connection.
        
        Args:
            path: Path to the SQLite database file. Defaults to in-memory.
        """
        self.path = path
        self.connection: Optional[sqlite3.Connection] = None
        self._initialized = False
    
    async def connect(self) -> None:
        """Establish a database connection and initialize tables."""
        loop = asyncio.get_event_loop()
        self.connection = await loop.run_in_executor(
            None, sqlite3.connect, self.path
        )
        await self._initialize_tables()
    
    async def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            await loop.run_in_executor(None, self.connection.close)
            self.connection = None
    
    async def _initialize_tables(self) -> None:
        """Initialize all database tables if they don't exist."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        async with self.connection:  # type: ignore
            # Sessions table
            await loop.run_in_executor(
                None,
                self.connection.execute,
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            
            # Tasks table
            await loop.run_in_executor(
                None,
                self.connection.execute,
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            
            # Events table
            await loop.run_in_executor(
                None,
                self.connection.execute,
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    agent_id TEXT,
                    task_id TEXT,
                    data TEXT
                )
                """
            )
            
            # Agent configurations table
            await loop.run_in_executor(
                None,
                self.connection.execute,
                """
                CREATE TABLE IF NOT EXISTS agent_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    role TEXT NOT NULL,
                    instructions TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
                """
            )
        
        self._initialized = True