"""Event Repository - event store for audit trail and session resumption."""

import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from .database import Database


class EventRepository:
    """Event store for audit trail and session resumption."""
    
    def __init__(self, database: Database):
        """Initialize the event repository."""
        self.db = database
    
    async def save_event(self, event: dict) -> None:
        """Save an event.
        
        Args:
            event: Event dictionary with timestamp, event_type, agent_id, task_id, data
        """
        await self.db.connect()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.db.connection.execute,
            """
            INSERT INTO events (timestamp, event_type, agent_id, task_id, data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.get("timestamp"),
                event.get("event_type"),
                event.get("agent_id"),
                event.get("task_id"),
                json.dumps(event.get("data", {})),
            ),
        )
    
    async def get_events_by_agent(self, agent_id: str) -> List[dict]:
        """Get all events for a specific agent."""
        await self.db.connect()
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(
            None,
            self.db.connection.execute,
            "SELECT timestamp, event_type, task_id, data FROM events WHERE agent_id = ? ORDER BY timestamp",
            (agent_id,),
        )
        rows = await loop.run_in_executor(None, cursor.fetchall)
        return [
            {
                "timestamp": row[0],
                "event_type": row[1],
                "task_id": row[2],
                "data": json.loads(row[3]) if row[3] else {},
            }
            for row in rows
        ]
    
    async def get_recent_events(self, limit: int = 100) -> List[dict]:
        """Get the most recent events."""
        await self.db.connect()
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(
            None,
            self.db.connection.execute,
            "SELECT timestamp, event_type, agent_id, task_id, data FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = await loop.run_in_executor(None, cursor.fetchall)
        return [
            {
                "timestamp": row[0],
                "event_type": row[1],
                "agent_id": row[2],
                "task_id": row[3],
                "data": json.loads(row[4]) if row[4] else {},
            }
            for row in rows
        ]