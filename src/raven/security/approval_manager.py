"""Approval Manager - manages approval workflow for dangerous operations."""

from __future__ import annotations

import asyncio
from typing import Dict, Any, Optional
import json


class ApprovalManager:
    """Manages approval workflow for dangerous operations."""
    
    def __init__(self, app=None):
        """Initialize the approval manager."""
        self.app = app
        self.pending_approvals: Dict[str, dict] = {}
        self._approval_counter = 0
    
    async def request_approval(self, 
                               operation_id: str, 
                               command: str, 
                               description: str) -> bool:
        """Request user approval for a dangerous operation.
        
        Args:
            operation_id: Unique identifier for this operation
            command: The command to be executed
            description: Human-readable description of what the command does
            
        Returns:
            True if approved, False if denied or timed out
        """
        self._approval_counter += 1
        pending_id = f"{operation_id}_{self._approval_counter}"
        
        self.pending_approvals[pending_id] = {
            "command": command,
            "description": description,
            "timestamp": asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0,
            "status": "pending",
        }
        
        # In a Textual app, we would render a confirmation dialog here
        # For now, we'll simulate with a console input
        if self.app:
            # Render dialog through Textual app
            # This is a placeholder - actual implementation would use app methods
            pass
        
        # For non-Textual environments, ask via console
        # return await self._console_approval(pending_id)
        
        # Default: return False for testing; in real app, user would approve
        return False
    
    async def _console_approval(self, pending_id: str) -> bool:
        """Get approval via console input (fallback for non-Textual environments)."""
        approval = self.pending_approvals.get(pending_id, {})
        
        print("\n" + "="*60)
        print("APPROVAL REQUIRED")
        print("="*60)
        print(f"Description: {approval.get('description', '')}")
        print(f"Command: {approval.get('command', '')}")
        print("\nApprove? (yes/no)")
        
        try:
            response = input().strip().lower()
            if response in ("yes", "y"):
                approval["status"] = "approved"
                return True
            else:
                approval["status"] = "denied"
                return False
        except (KeyboardInterrupt, EOFError):
            approval["status"] = "cancelled"
            return False
    
    def approve(self, operation_id: str) -> bool:
        """Mark an operation as approved (synchronous, for Textual callbacks)."""
        for pid, approval in self.pending_approvals.items():
            if operation_id in pid:
                approval["status"] = "approved"
                return True
        return False
    
    def deny(self, operation_id: str) -> bool:
        """Mark an operation as denied."""
        for pid, approval in self.pending_approvals.items():
            if operation_id in pid:
                approval["status"] = "denied"
                return True
        return False
    
    def get_pending(self) -> Dict[str, dict]:
        """Get all pending approvals."""
        return self.pending_approvals
    
    def clear(self, operation_id: str) -> None:
        """Clear a pending approval."""
        for pid in list(self.pending_approvals.keys()):
            if operation_id in pid:
                del self.pending_approvals[pid]
                break