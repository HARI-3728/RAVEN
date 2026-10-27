# RAVEN Security Document

## 1. Security Philosophy

RAVEN is designed with security as a first-class concern. The terminal-based nature of the application presents unique security considerations:

- **No hardcoded credentials**: API keys and secrets are never embedded in source code
- **Principle of least privilege**: Agents only access files and commands necessary for their assigned tasks
- **Explicit approvals**: Dangerous operations require user confirmation before execution
- **Defense in depth**: Multiple layers of validation (path, command, approval)
- **Auditability**: All significant events are logged with context for audit trails

## 2. Secrets Management

### 2.1. Core Principle: Never Store Secrets in Source Control or SQLite

- API keys are sourced exclusively from environment variables at runtime
- Configuration files contain only references to environment variable names, never actual values
- `.env.example` provides placeholder variable names only (never real keys)
- Production environments must set environment variables before running RAVEN

### 2.2. Environment Variable Source

| Secret Type | Environment Variable | Required For |
|-------------|---------------------|-------------|
| OpenAI API Key | `OPENAI_API_KEY` | All OpenAI provider integrations |
| Google Gemini Key | `GEMINI_API_KEY` | All Gemini provider integrations |
| Anthropic API Key | `ANTHROPIC_API_KEY` | All Anthropic provider integrations |
| OpenAI-Compatible Key | `OPENAI_COMPATIBLE_API_KEY` | OpenAI-compatible API integrations |
| OpenAI-Compatible Base URL | `OPENAI_COMPATIBLE_BASE_URL` | OpenAI-compatible API base URL override |
| Local Model Path | Not applicable | Local/offline model integrations |

### 2.3. Runtime Credential Loading

```python
import os

def load_api_key(provider: str) -> Optional[str]:
    """Load API key from environment variables."""
    env_vars = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY", 
        "anthropic": "ANTHROPIC_API_KEY",
        "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
    }
    
    var_name = env_vars.get(provider.lower())
    if not var_name:
        return None
    
    key = os.environ.get(var_name)
    if not key:
        raise ValueError(
            f"No {provider} API key found in environment variable '{var_name}'. "
            "Set this variable before running RAVEN."
        )
    
    return key
```

### 2.4. .env File Handling

- `.env` files are gitignored and never committed
- `.env.example` is committed as a template with placeholder names only
- Users copy `.env.example` to `.env` and fill in their actual keys
- The `.env` file path is never hardcoded; loading respects standard `.env` discovery

### 2.5. SQLite Storage Policy

- **API secrets are NEVER stored in SQLite records**
- Session metadata (agent config, task state, events) may be stored in SQLite
- Only non-sensitive configuration is persisted
- If session persistence requires provider references, only provider names and model IDs are stored—not credentials
- SQLite database file is user-local and not uploaded or shared

```python
# Correct: Store only non-sensitive data
session_data = {
    "agent_name": "agent_1",
    "provider": "openai",
    "model": "gpt-4o",
    "role": "developer",
    # NOT stored: api_key, secret_key, token
}

# Incorrect (never do this):
session_data = {
    "agent_name": "agent_1",
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": os.environ["OPENAI_API_KEY"],  # NEVER store this
}
```

## 3. Command Validation

### 3.1. Command Validator (`raven/security/command_validator.py`)

All shell commands executed by RAVEN agents pass through a validator that:

- Whitelists allowed commands and arguments
- Blocks dangerous patterns (shell injection, data exfiltration, etc.)
- Validates working directory boundaries
- Logs command attempts for audit

```python
import re
import fnmatch

class CommandValidator:
    """Validates shell commands before execution."""
    
    # Patterns that are always blocked
    BLOCKED_PATTERNS = [
        r";\s*(rm|dd|format|del)\s",  # Injection of destructive commands
        r"\|.*\s*(curl|wget|nc)\s",    # Pipe to external fetches
        r"\$\(",                         # Command substitution
        r"`[^`]*`",                       # Backtick command substitution
        r">\s*/dev/null",                # Suppress output to null
        r"&>.*",                         # Redirect and merge stderr
    ]
    
    # Allowed command categories
    ALLOWED_COMMANDS = {
        "git": ["status", "diff", "log", "checkout", "branch", "merge"],
        "python": ["-m", "pip", "install", "uninstall"],
        "ls": ["-la", "-l", ""],
        "cat": [""],
        "cd": [""],
    }
    
    def validate(self, command: str, cwd: str, allowed_dir: str) -> tuple:
        """Validate a command and return (approved, reason).
        
        Returns:
            (True, "") if command is approved
            (False, reason) if command is rejected
        """
        # Check for blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command blocked: matches pattern {pattern}"
        
        # Parse command
        parts = command.split()
        if not parts:
            return False, "Empty command"
        
        cmd = parts[0]
        args = parts[1:]
        
        # Check working directory boundary
        abs_cwd = os.path.abspath(cwd)
        abs_allowed = os.path.abspath(allowed_dir)
        if not abs_cwd.startswith(abs_allowed):
            return False, f"Working directory outside allowed boundary: {cwd}"
        
        # Check command is in allowed list
        if cmd in self.ALLOWED_COMMANDS:
            # Validate arguments against allowed list
            allowed_args = self.ALLOWED_COMMANDS[cmd]
            for arg in args:
                if arg not in allowed_args and not self._is_safe_arg(cmd, arg):
                    return False, f"Argument not allowed for {cmd}: {arg}"
        else:
            # Unknown commands require explicit approval
            return False, f"Unknown command '{cmd}' requires approval"
        
        return True, ""
    
    def _is_safe_arg(self, cmd: str, arg: str) -> bool:
        """Check if an argument is safe for a command."""
        # Allow absolute paths within project
        if os.path.isabs(arg) and not arg.startswith("/tmp/"):
            return False  # Block absolute paths
        # Allow relative paths
        if not os.path.isabs(arg):
            return True
        return False
```

### 3.2. Approval Manager (`raven/security/approval_manager.py`)

Dangerous commands require explicit user approval before execution:

```python
class ApprovalManager:
    """Manages approval workflow for dangerous operations."""
    
    def __init__(self, app):
        self.app = app
        self.pending_approvals: Dict[str, dict] = {}
    
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
        # Show approval dialog in TUI
        self.pending_approvals[operation_id] = {
            "command": command,
            "description": description,
            "timestamp": datetime.now(),
        }
        
        # Render approval dialog in Textual
        # User responds via dialog buttons
        result = await self.app.render_confirmation_dialog(
            title="Approve Dangerous Operation",
            text=f"Description: {description}\n\nCommand: `{command}`\n\nProceed?",
            accept_label="Approve",
            decline_label="Deny"
        )
        
        if result:
            # Remove from pending and return True
            self.pending_approvals.pop(operation_id, None)
            return True
        else:
            self.pending_approvals.pop(operation_id, None)
            return False
```

## 4. Path Validation

### 4.1. Path Validator (`raven/security/path_validator.py`)

All file paths are validated to prevent path traversal and ensure they're within the project boundary.

```python
import os

class PathValidator:
    """Validates file paths for security boundaries."""
    
    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
    
    def validate(self, path: str, operation: str = "read") -> tuple:
        """Validate a file path and return (approved, resolved_path, reason).
        
        Args:
            path: The file path to validate (may be relative or absolute)
            operation: The operation being performed ("read", "write", "delete", "edit")
            
        Returns:
            (True, resolved_path) if valid
            (False, None, reason) if invalid
        """
        # Resolve relative to project root
        if not os.path.isabs(path):
            resolved = os.path.normpath(os.path.join(self.project_root, path))
        else:
            resolved = os.path.normpath(path)
        
        # Check for path traversal outside project root
        if not resolved.startswith(self.project_root + os.sep) and resolved != self.project_root:
            return False, None, f"Path traversal detected: {path} outside project root"
        
        # Check file exists for write/delete operations
        if operation in ("write", "delete", "edit") and not os.path.exists(resolved) and operation != "write":
            # Write is always allowed to create new files within project
            if not path.startswith(".") and not "/" in path.replace(".", ""):
                return False, None, f"Cannot determine target for {operation}"
        
        # Check for dangerous file types
        dangerous_extensions = [".exe", ".sh", ".bash", ".cmd", ".com"]
        _, ext = os.path.splitext(resolved)
        if ext.lower() in dangerous_extensions:
            return False, None, f"Dangerous file type: {ext}"
        
        # Check for symlink traversal
        if os.path.islink(resolved):
            # Follow symlink but ensure it stays within project
            real_path = os.path.realpath(resolved)
            if not real_path.startswith(self.project_root + os.sep) and real_path != self.project_root:
                return False, None, f"Symlink traversal: {path} -> {real_path}"
        
        return True, resolved, ""
    
    def validate_read(self, path: str) -> tuple:
        """Validate path for reading."""
        return self.validate(path, "read")
    
    def validate_write(self, path: str) -> tuple:
        """Validate path for writing/creating."""
        return self.validate(path, "write")
    
    def validate_delete(self, path: str) -> tuple:
        """Validate path for deletion."""
        return self.validate(path, "delete")
    
    def validate_edit(self, path: str) -> tuple:
        """Validate path for editing."""
        return self.validate(path, "edit")
```

## 5. Git Integration Security

### 5.1. Change Tracking and Checkpoints

RAVEN uses Git for checkpointing and change recovery, with security safeguards:

- **Diffs are reviewed before applying**: No sensitive changes are applied without user review
- **Git checkpoint commands require approval**: `git reset`, `git checkout`, `git clean` require explicit approval
- **No automatic force pushes**: All Git operations are conservative and user-reviewed

### 5.2. Git Manager Safeguards

```python
class GitManager:
    """Git operations with security safeguards."""
    
    def __init__(self, project_root: str, approval_manager):
        self.project_root = project_root
        self.approval_manager = approval_manager
    
    async def safe_commit(self, message: str) -> bool:
        """Create a git commit with approval."""
        # Show diff to user for review
        diff = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=self.project_root,
            capture_output=True, text=True
        )
        
        # Present diff in TUI and ask for confirmation
        approved = await self.approval_manager.request_approval(
            operation_id=f"commit_{hash(diff.stdout)}",
            command=f"git commit -m '{message}'",
            description=f"Commit changes:\n{diff.stdout[-200:]}..."
        )
        
        if approved:
            subprocess.run(["git", "commit", "-m", message], cwd=self.project_root, check=True)
            return True
        return False
    
    async def safe_reset(self, target: str) -> bool:
        """Reset to a git checkpoint with approval."""
        # Never auto-reset without explicit approval
        approved = await self.approval_manager.request_approval(
            operation_id=f"reset_{target}",
            command=f"git reset --{target}",
            description=f"Reset repository to {target}"
        )
        
        if approved:
            subprocess.run(["git", "reset", "--", target], cwd=self.project_root, check=True)
            return True
        return False
```

## 6. Concurrency and File Editing

### 6.1. Preventing Uncontrolled Concurrent Edits

- **File-level locks**: When an agent begins editing a file, a lock is acquired
- **Edit conflict detection**: If two agents attempt to modify the same file, the second agent waits or aborts
- **Change tracking**: All modifications tracked via git_tools; diffs compared before applying

```python
class FileLockManager:
    """Manages file locks to prevent uncontrolled concurrent edits."""
    
    def __init__(self):
        self.locks: Dict[str, str] = {}  # path -> agent_id
    
    def try_lock(self, path: str, agent_id: str, timeout: int = 30) -> bool:
        """Try to acquire a lock on a file.
        
        Returns:
            True if lock acquired, False if another agent holds the lock
        """
        if path in self.locks and self.locks[path] != agent_id:
            return False  # Another agent holds the lock
        self.locks[path] = agent_id
        return True
    
    def release(self, path: str, agent_id: str) -> None:
        """Release a lock on a file."""
        if self.locks.get(path) == agent_id:
            del self.locks[path]
    
    def check_conflict(self, path: str, agent_id: str) -> bool:
        """Check if an agent already holds a lock on this path."""
        return self.locks.get(path) == agent_id
```

### 6.2. Edit Workflow

1. Agent requests lock on target file
2. If lock available, agent acquires lock and proceeds with edits
3. Agent generates diff of intended changes
4. System presents diff to user for review (if changes are sensitive)
5. User approves or rejects changes
6. If approved, changes are applied and lock released
7. If rejected, agent is notified and must revise approach
8. Lock is always released on completion or failure
```

## 7. Audit Logging

### 7.1. Structured Logging

All security-relevant events are logged structurally:

```
{
    "timestamp": "2024-01-15T10:30:45Z",
    "level": "INFO",
    "event": "command_approved" | "command_rejected" | "api_key_validated" | "session_started" | "session_stopped",
    "agent_id": "agent_1" | "system",
    "provide": "openai" | "anthropic" | ...,
    "model": "gpt-4o" | "claude-3-opus-20240229" | ...,
    "path": "/path/to/file" | null,
    "command": "git status" | "rm ..." | null,
    "outcome": "approved" | "rejected" | "success" | "failed",
    "user_id": current_user
}
```

### 7.2. Log Output

- Logs output to terminal with Rich formatting
- Sensitive fields (API keys, passwords) are masked in log output
- Log level configurable via configuration
- Audit log file can be specified for persistent record-keeping (no secrets stored)

## 8. Security Checklist for New Features

Before any new feature is merged, verify:

- [ ] No API keys or secrets are hardcoded
- [ ] Environment variables are used for all credentials
- [ ] Command validator blocks injection patterns
- [ ] Path validator prevents traversal outside project root
- [ ] Dangerous operations require explicit user approval
- [ ] File locks prevent uncontrolled concurrent edits
- [ ] Git operations require user review of diffs
- [ ] Log output masks sensitive data
- [ ] .env.example contains placeholder names only
- [ ] SQLite stores no API secrets
- [ ] All security boundaries tested with edge cases