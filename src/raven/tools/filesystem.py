"""Filesystem Tools - file system operations with safety guards and path validation.

Provides controlled access to project files with:
- Path traversal prevention
- Project boundary enforcement
- Git diff inspection
- Approved test execution
- File modification tracking
- Change review support
"""

from __future__ import annotations

import os
import asyncio
import subprocess
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from ..security.path_validator import PathValidator
from ..security.command_validator import CommandValidator


class FileSystemTools:
    """File system operations with safety guards and path validation.
    
    Key features:
    - Project root boundary enforcement
    - Path traversal prevention
    - Git diff inspection for change tracking
    - Permitted test execution with boundaries
    - File modification tracking and history
    - Change review support (diffs before writes)
    """
    
    def __init__(self, project_root: str, path_validator: Optional[PathValidator] = None,
                 command_validator: Optional[CommandValidator] = None):
        """Initialize filesystem tools.
        
        Args:
            project_root: The project root directory for boundary checking
            path_validator: Optional PathValidator instance
            command_validator: Optional CommandValidator instance
        """
        self.project_root = os.path.abspath(project_root)
        self.path_validator = path_validator or PathValidator(project_root)
        self.command_validator = command_validator or CommandValidator()
        self._file_hashes: Dict[str, str] = {}  # Track file hashes for change detection
        self._modified_files: List[dict] = []  # Track pending modifications
    
    def read_file(self, path: str, max_size: int = 10 * 1024 * 1024) -> Tuple[bool, Optional[str], str]:
        """Read a file from the project with path validation.
        
        Args:
            path: File path (relative to project_root or absolute within project)
            max_size: Maximum file size to read (default 10MB)
            
        Returns:
            (success, content, message) tuple
        """
        # Validate the path is within project boundaries
        is_valid, resolved_path, reason = self.path_validator.validate_read(path)
        
        if not is_valid:
            return False, None, reason
        
        # Check file size
        try:
            file_size = os.path.getsize(resolved_path)
        except OSError:
            return False, None, f"Cannot access file: {path}"
        
        if file_size > max_size:
            return False, None, f"File too large: {file_size} bytes (max {max_size})"
        
        # Read the file content
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return True, content, ""
        except UnicodeDecodeError:
            # Try reading as binary and decoding with replacement
            try:
                with open(resolved_path, 'rb') as f:
                    binary_content = f.read()
                content = binary_content.decode('utf-8', errors='replace')
                return True, content, ""
            except Exception as e:
                return False, None, f"Cannot read file (encoding error): {str(e)}"
            except Exception as e:
                return False, None, f"Cannot read file: {str(e)}"
        except Exception as e:
            return False, None, f"Cannot read file: {str(e)}"
    
    def write_file(self, path: str, content: str, create_backup: bool = True) -> Tuple[bool, str]:
        """Write content to a file with path validation and optional backup.
        
        Args:
            path: File path (relative to project_root)
            content: Content to write
            create_backup: Whether to create a backup of existing file
            
        Returns:
            (success, message) tuple
        """
        # Validate the path is within project boundaries
        is_valid, resolved_path, reason = self.path_validator.validate_write(path)
        
        if not is_valid:
            return False, reason
        
        # Create backup if file exists and backup enabled
        if create_backup and os.path.exists(resolved_path):
            try:
                backup_path = resolved_path + ".bak"
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                # Record the backup for potential rollback
                self._modified_files.append({
                    "action": "write_backup",
                    "path": path,
                    "backup_path": backup_path,
                    "original_content": original_content,
                })
            except Exception as e:
                return False, f"Cannot create backup: {str(e)}"
        
        # Write the new content
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(resolved_path)
            if parent_dir and not os.path.isdir(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Track the modification
            self._modified_files.append({
                "action": "write",
                "path": path,
                "resolved_path": resolved_path,
                "new_content": content,
                "old_content": self._get_file_content_safe(resolved_path) if os.path.exists(resolved_path) else "",
            })
            
            # Update hash tracking
            try:
                import hashlib
                with open(resolved_path, 'rb') as f:
                    self._file_hashes[path] = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass
            
            return True, "File written successfully"
        except Exception as e:
            # Attempt rollback from backup if created
            self._rollback_last_operation()
            return False, f"Cannot write file: {str(e)}"
    
    def _get_file_content_safe(self, path: str) -> str:
        """Safely get file content for tracking.
        
        Args:
            path: Resolved file path
            
        Returns:
            File content or empty string
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    def _rollback_last_operation(self) -> None:
        """Roll back the last file modification operation."""
        if not self._modified_files:
            return
        
        last_op = self._modified_files[-1]
        
        if last_op["action"] == "write_backup":
            # Remove the backup file
            try:
                if os.path.exists(last_op["backup_path"]):
                    os.remove(last_op["backup_path"])
            except Exception:
                pass
            self._modified_files.pop()
        elif last_op["action"] == "write":
            # Attempt restoration from old content
            try:
                if os.path.exists(last_op["resolved_path"]):
                    with open(last_op["resolved_path"], 'w', encoding='utf-8') as f:
                        f.write(last_op.get("old_content", ""))
            except Exception:
                pass
            self._modified_files.pop()
    
    def get_diff(self, path: str, backup: bool = True) -> Tuple[bool, Optional[str], str]:
        """Get a diff of changes to a file compared to backup or previous version.
        
        Args:
            path: File path
            backup: Whether to compare against .bak backup
            
        Returns:
            (success, diff_content, message) tuple
        """
        is_valid, resolved_path, reason = self.path_validator.validate_read(path)
        
        if not is_valid:
            return False, None, reason
        
        # Determine what to compare against
        if backup:
            compare_path = resolved_path + ".bak"
        else:
            # Get previous version from hash tracking
            compare_path = None
        
        if not os.path.exists(resolved_path):
            return False, None, f"File not found: {path}"
        
        # Read current content
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except Exception as e:
            return False, None, f"Cannot read current file: {str(e)}"
        
        # Read backup/previous content
        if backup and os.path.exists(compare_path):
            try:
                with open(compare_path, 'r', encoding='utf-8') as f:
                    previous_content = f.read()
            except Exception:
                previous_content = ""
        else:
            previous_content = ""
        
        # Generate unified diff
        if current_content == previous_content:
            return True, "", "No changes detected"
        
        # Generate diff text
        diff_lines = self._generate_diff(previous_content, current_content)
        diff_text = "\n".join(diff_lines)
        
        return True, diff_text, "Diff generated successfully"
    
    def _generate_diff(self, old: str, new: str) -> List[str]:
        """Generate a unified diff between two strings.
        
        Args:
            old: Original content
            new: New content
            
        Returns:
            List of diff lines
        """
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        diff = []
        diff.append("--- a/" + os.path.basename(old) if old else "--- /dev/null")
        diff.append("+++ b/" + os.path.basename(new) if new else "+++ /dev/null")
        
        # Simple diff generation
        old_nonempty = [l for l in old_lines if l.strip()]
        new_nonempty = [l for l in new_lines if l.strip()]
        
        # Count lines
        old_len = len(old_lines)
        new_len = len(new_lines)
        
        diff.append(f"@@ -{old_len - len(old_nonempty):5d} +{new_len - len(new_nonempty):5d} @@")
        
        # Add changed lines
        for i, (old_l, new_l) in enumerate(zip(old_lines, new_lines)):
            if old_l != new_l:
                if old_l.startswith(" ") and new_l.startswith(" "):
                    # Both context lines - keep as is
                    pass
                elif not old_l.strip() and new_l.strip():
                    # Line added
                    diff.append(f"+{new_l}", end="")
                elif old_l.strip() and not new_l.strip():
                    # Line removed
                    diff.append(f"-{old_l}", end="")
                elif old_l.strip() and new_l.strip():
                    # Line changed
                    diff.append(f"-{old_l}", end="")
                    diff.append(f"+{new_l}", end="")
        
        return diff
    
    def list_directory(self, path: str = ".", recursive: bool = False) -> Tuple[bool, Optional[List[str]], str]:
        """List files in a directory with path validation.
        
        Args:
            path: Directory path (relative to project_root)
            recursive: Whether to recursively list
            
        Returns:
            (success, file_list, message) tuple
        """
        is_valid, resolved_path, reason = self.path_validator.validate_read(path)
        
        if not is_valid:
            return False, None, reason
        
        if not os.path.isdir(resolved_path):
            return False, None, f"Not a directory: {path}"
        
        try:
            if recursive:
                files = []
                for root, dirs, filenames in os.walk(resolved_path):
                    # Skip hidden directories and certain system dirs
                    dirs[:] = [d for d in dirs if not d.startswith('.') or d in ('.git',)]
                    for filename in filenames:
                        fpath = os.path.join(root, filename)
                        relpath = os.path.relpath(fpath, self.project_root)
                        # Skip .git directory
                        if '.git' in relpath:
                            continue
                        files.append(relpath)
                return True, files, ""
            else:
                files = os.listdir(resolved_path)
                # Filter to only show files (not directories) or include both
                return True, files, ""
        except Exception as e:
            return False, None, f"Cannot list directory: {str(e)}"
    
    def get_project_root(self) -> str:
        """Get the project root directory."""
        return self.project_root
    
    def get_modified_files(self) -> List[dict]:
        """Get list of recently modified files with change info.
        
        Returns:
            List of dicts with modification info
        """
        return self._modified_files[:]
    
    def reset_modifications(self) -> None:
        """Reset the modification tracking."""
        self._modified_files = []
        self._file_hashes = {}


class GitTools:
    """Git operations for checkpoint management, diffing, and change tracking.
    
    Provides Git integration with:
    - Repository status checking
    - Diff generation for change review
    - Commit operations with approval
    - Branch and tag management
    - Gitignore respect
    """
    
    def __init__(self, project_root: str, path_validator: PathValidator):
        """Initialize Git tools.
        
        Args:
            project_root: Project root directory (should be a git repo)
            path_validator: PathValidator for boundary checking
        """
        self.project_root = os.path.abspath(project_root)
        self.path_validator = path_validator
        self._repo = None
        self._init_repo()
    
    def _init_repo(self) -> None:
        """Initialize git repository detection."""
        try:
            import git
            self._repo = git.Repo(self.project_root)
        except ImportError:
            # git not installed, will handle gracefully
            self._repo = None
        except git.NoSuchPathError:
            self._repo = None
        except Exception:
            self._repo = None
    
    @property
    def repo(self):
        """Get the git repo instance."""
        return self._repo
    
    def is_git_repo(self) -> bool:
        """Check if the project root is a git repository."""
        return self._repo is not None
    
    def get_status(self) -> Tuple[bool, Optional[str], str]:
        """Get git repository status.
        
        Returns:
            (is_repo, status_text, message) tuple
        """
        if not self._repo:
            return False, None, "Not a git repository"
        
        try:
            status = self._repo.status()
            # Summarize status
            modified = [f for f in status if status[f] in ('M', 'A', 'D')]
            untracked = [f for f in status if status[f] == 'U']
            
            lines = []
            if modified:
                lines.append(f"Modified: {', '.join(modified[:5])}" + (f" and {len(modified)-5} more" if len(modified) > 5 else ""))
            if untracked:
                lines.append(f"Untracked: {', '.join(untracked[:5])}" + (f" and {len(untracked)-5} more" if len(untracked) > 5 else ""))
            
            status_text = "; ".join(lines) if lines else "Working directory clean"
            return True, status_text, ""
        except Exception as e:
            return False, None, f"Error getting git status: {str(e)}"
    
    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> Tuple[bool, Optional[str], str]:
        """Get git diff for files.
        
        Args:
            file_path: Specific file to diff (None = all changes)
            staged: Whether to show staged changes
            
        Returns:
            (success, diff_text, message) tuple
        """
        if not self._repo:
            return False, None, "Not a git repository"
        
        try:
            if file_path:
                # Diff for specific file
                try:
                    diffs = self._repo.diff(file_path)
                    if staged:
                        staged_diffs = self._repo.head.diff(file_path)
                        diffs = list(diffs) + list(staged_diffs)
                    
                    if diffs:
                        diff_text = "\n".join([d.diff.decode('utf-8', errors='replace') for d in diffs])
                        return True, diff_text, ""
                    else:
                        return True, "", "No changes"
                except git.GitCommandError:
                    return True, "", f"No git diff for: {file_path}"
            else:
                # Diff for all changes
                if staged:
                    diffs = self._repo.git.diff('--cached').split('\n\n') if self._repo.git.diff('--cached') else []
                else:
                    diffs = self._repo.git.diff().split('\n\n') if self._repo.git.diff() else []
                
                if diffs:
                    # Combine all diffs
                    diff_text = "\n\n".join(diffs)
                    return True, diff_text, ""
                else:
                    return True, "", "No changes"
        except Exception as e:
            return False, None, f"Error getting git diff: {str(e)}"
    
    def get_log(self, max_count: int = 10, file_filter: Optional[str] = None) -> Tuple[bool, Optional[str], str]:
        """Get git commit history.
        
        Args:
            max_count: Maximum number of commits to return
            file_filter: Optional file filter
            
        Returns:
            (success, log_text, message) tuple
        """
        if not self._repo:
            return False, None, "Not a git repository"
        
        try:
            commits = list(self._repo.iter_commits(max_count=max_count))
            
            lines = []
            for commit in commits:
                # Get stats for this commit
                stats = commit.stats
                file_changed = stats.total.get('files', 0) if stats else 0
                
                # Get modified files in this commit
                try:
                    diff = commit.diff(None, file_filter)
                    modified_files = [str(d.a_path) for d in diff] if diff else []
                except Exception:
                    modified_files = []
                
                commit_info = (
                    f"commit {commit.hexsha[:8]}\n"
                    f"Author: {commit.author}\n"
                    f"Date: {commit.committed_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Files: {file_changed}\n"
                    f"Message: {commit.message.strip()[:80]}..."
                )
                lines.append(commit_info)
            
            return True, "\n\n".join(lines), ""
        except Exception as e:
            return False, None, f"Error getting git log: {str(e)}"
    
    def get_branch(self) -> Tuple[bool, Optional[str], str]:
        """Get current branch name."""
        if not self._repo:
            return False, None, "Not a git repository"
        
        try:
            branch = self._repo.head.ref.name
            return True, branch, ""
        except Exception as e:
            return False, None, f"Error getting branch: {str(e)}"
    
    def is_file_tracked(self, file_path: str) -> bool:
        """Check if a file is tracked by git."""
        if not self._repo:
            return False
        
        try:
            # Make path relative to repo root
            rel_path = os.path.relpath(file_path, self.project_root)
            return self._repo.git.ls_files(rel_path) != ''
        except Exception:
            return False
    
    def get_untracked_files(self) -> List[str]:
        """Get list of untracked files."""
        if not self._repo:
            return []
        
        try:
            return self._repo.untracked_files
        except Exception:
            return []