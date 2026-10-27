"""Task Repository - persists and retrieves tasks, events, and results."""

import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from .database import Database


class TaskRepository:
    """Persists and retrieves tasks, events, and results."""
    
    def __init__(self, database: Database):
        """Initialize the task repository."""
        self.db = database
    
    async def save_task(self, task: dict) -> None:
        """Save a task.
        
        Args:
            task: Task dictionary with id, description, role, status, etc.
        """
        await self.db.connect()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.db.connection.execute,
            """
            INSERT OR REPLACE INTO tasks (id, description, role, status, result, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.get("id"),
                task.get("description"),
                task.get("role"),
                task.get("status", "pending"),
                task.get("result"),
                task.get("created_at"),
                task.get("updated_at"),
            ),
        )
    
    async def get_pending_tasks(self) -> List[dict]:
        """Get all pending tasks."""
        await self.db.connect()
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(
            None,
            self.db.connection.execute,
            "SELECT id, description, role, status FROM tasks WHERE status = 'pending'",
        )
        rows = await loop.run_in_executor(None, cursor.fetchall)
        return [
            {"id": row[0], "description": row[1], "role": row[2], "status": row[3]}
            for row in rows
        ]
    
    async def get_task(self, task_id: str) -> Optional[dict]:
        """Get a task by ID."""
        await self.db.connect()
        loop = asyncio.get_event_loop()
        cursor = await loop.run_in_executor(
            None,
            self.db.connection.execute,
            "SELECT id, description, role, status, result FROM tasks WHERE id = ?",
            (task_id,),
        )
        row = await loop.run_in_executor(None, cursor.fetchone)
        if row:
            return {"id": row[0], "description": row[1], "role": row[2], "status": row[3], "result": row[4]}
        return None