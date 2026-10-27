"""Command Validator - validates commands before execution, especially dangerous ones."""

from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Tuple


class CommandValidator:
    """Validates shell commands before execution."""
    
    # Patterns that are always blocked due to security risks
    BLOCKED_PATTERNS = [
        # Shell injection patterns
        r";\s*(rm|dd|format|del|mv)\s",  # Destructive command injection
        r"&&\s*(rm|dd|format|del|mv)\s",  # Destructive with AND
        r"\|\s*(rm|dd|format|del|mv)\s",  # Destructive piped
        r"\|\|.*(rm|dd|format|del|mv)",   # Destructive with OR
        
        # Data exfiltration
        r"\|\s*(curl|wget|nc|ftp)\s",    # Pipe to external transfer
        r">\s*/\S+/(data|upload|export)", # Upload to external service
        
        # Command substitution
        r"\$\s*\(",                       # $() command substitution
        r"`[^`]*`",                       # Backtick substitution
        
        # Dangerous wildcards
        r"\brm\s+/-f\b",                 # rm -f
        r"\brm\s+/-r\b",                 # rm -r
        r"\brm\s+\*/",                   # rm with globstar
        
        # Fork bombs and extreme operations
        r":\(\)\{.*\}",                   # Fork bomb pattern
    ]
    
    # Commands that require explicit approval
    APPROVED_COMMANDS = {
        "git": ["status", "diff", "log", "branch", "checkout", "merge", "reset"],
        "python": ["-m", "pip", "install", "uninstall", "run"],
        "ls": ["-la", "-l", "-h", ""],
        "cat": [""],
        "cd": [""],
        "mkdir": ["-p"],
    }
    
    def __init__(self):
        """Initialize the command validator."""
        pass
    
    def validate(self, 
                 command: str, 
                 cwd: str, 
                 allowed_dir: str) -> Tuple[bool, str]:
        """Validate a command and return (approved, reason).
        
        Args:
            command: The command string to validate
            cwd: Current working directory
            allowed_dir: Allowed project directory boundary
            
        Returns:
            (True, "") if command is approved
            (False, reason) if command is rejected
        """
        # Normalize paths
        abs_cwd = os.path.abspath(cwd)
        abs_allowed = os.path.abspath(allowed_dir)
        
        # Check working directory boundary
        if not abs_cwd.startswith(abs_allowed + os.sep) and abs_cwd != abs_allowed:
            return False, f"Working directory outside allowed boundary: {cwd}"
        
        # Check for blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command blocked: matches dangerous pattern {pattern}"
        
        # Parse the command
        parts = command.split()
        if not parts:
            return False, "Empty command"
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Check if command is in allowed list
        if cmd in self.APPROVED_COMMANDS:
            # Validate arguments against allowed list
            allowed_args = self.APPROVED_COMMANDS[cmd]
            for arg in args:
                if arg not in allowed_args:
                    # Check if it's a safe relative path or known argument
                    if not self._is_safe_argument(cmd, arg):
                        return False, f"Argument not allowed for '{cmd}': {arg}"
        else:
            # Unknown commands require explicit approval
            return False, f"Unknown command '{cmd}' requires explicit approval"
        
        return True, ""
    
    def _is_safe_argument(self, cmd: str, arg: str) -> bool:
        """Check if an argument is safe for a given command."""
        # Allow absolute paths only within /tmp
        if os.path.isabs(arg) and not arg.startswith("/tmp/"):
            return False
        
        # Allow relative paths
        if not os.path.isabs(arg):
            return True
        
        # Allow specific known flags/arguments
        safe_flags = {
            "cat": ["-n", "-s", "-b"],
            "ls": ["-la", "-l", "-h", "-a", "-r", "-t"],
            "mkdir": ["-p"],
        }
        
        return arg in safe_flags.get(cmd, [])