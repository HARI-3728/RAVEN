"""Session Repository - persists and retrieves session metadata."""

import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from .database import Database


class SessionRepository:
    """Persists and retrieves session metadata."""
    
    def __init__(self, database: Database):
        """Initialize the session repository."""
        self.db = database
    
    async def save_session(self, session_id: str, config: dict) -> None:
        """Save a session configuration.
        
        Args:
            session_id: Unique session identifier
            config: Session configuration dictionary
        """
        await self.db.connect()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.db.connection.execute,
            """
            INSERT OR REPLACE INTO sessions (id, config, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                json.dumps(config),
                loop.time(),
                loop.time(),
            ),
        )
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a session configuration.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session configuration dictionary or None
        """
        await self.db.connect()
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(
            None,
            self.db.connection.execute,
            "SELECT config FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await loop.run_in_executor(None, cursor.fetchone)
        if row:
            return json.loads(row[0])
        return None
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        await self.db.connect()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.db.connection.execute,
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )