"""Coding Tools - real workspace tools for RAVEN's coding agent.

Provides safe, boundary-enforced tools for:
- Workspace exploration (listing directories and files)
- File reading and bounded editing
- Content search across project files
- Shell command execution with approval controls
- Test running with exit-code capture
- Git status and diff inspection
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path

from ..security.path_validator import PathValidator
from ..security.command_validator import CommandValidator
from ..tools.filesystem import FileSystemTools
from ..tools.permission_manager import PermissionManager


class ToolExecutionResult:
    """Structured result from a tool execution."""
    
    def __init__(
        self,
        tool_name: str,
        success: bool,
        output: str,
        error: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        approval_required: bool = False,
    ):
        self.tool_name = tool_name
        self.success = success
        self.output = output
        self.error = error
        self.data = data or {}
        self.approval_required = approval_required
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "data": self.data,
        }
        
    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error or self.output}"


class CodingTools:
    """Safe, controlled tools for inspecting and modifying a workspace."""

    def __init__(
        self,
        project_root: str,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        """Initialize coding tools.
        
        Args:
            project_root: Absolute or relative path to project root
            approval_callback: Optional callable(action, details) returning bool for sensitive ops
        """
        self.project_root = os.path.abspath(project_root)
        self.path_validator = PathValidator(self.project_root)
        self.command_validator = CommandValidator()
        self.filesystem_tools = FileSystemTools(self.project_root, self.path_validator, self.command_validator)
        self.permission_manager = PermissionManager(self.path_validator, self.command_validator)
        self.approval_callback = approval_callback
        
        # Track session actions for final reports
        self.changed_files: List[str] = []
        self.commands_executed: List[Dict[str, Any]] = []
        self.tests_executed: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Tool Schemas for Models
    # -------------------------------------------------------------------------

    @classmethod
    def get_tool_definitions(cls) -> List[Dict[str, Any]]:
        """Return tool definitions in standard OpenAI/Anthropic compatible format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "List files and subdirectories in a workspace path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative directory path (e.g. '.' or 'src/raven').",
                                "default": ".",
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum depth for listing (default: 2).",
                                "default": 2,
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read file contents within the workspace with line numbers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path to file to read.",
                            },
                            "start_line": {
                                "type": "integer",
                                "description": "Optional 1-indexed start line.",
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "Optional 1-indexed end line.",
                            },
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create a new file or completely overwrite an existing file in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path to destination file.",
                            },
                            "content": {
                                "type": "string",
                                "description": "Complete text content to write.",
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Replace a unique string with replacement text in an existing file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path to the file to edit.",
                            },
                            "old_string": {
                                "type": "string",
                                "description": "Exact text substring to be replaced (must be unique).",
                            },
                            "new_string": {
                                "type": "string",
                                "description": "New replacement text.",
                            },
                        },
                        "required": ["path", "old_string", "new_string"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "grep_search",
                    "description": "Search for text or regex pattern across workspace files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search term or regex pattern.",
                            },
                            "path": {
                                "type": "string",
                                "description": "Directory or file to search within (default: '.').",
                                "default": ".",
                            },
                            "case_sensitive": {
                                "type": "boolean",
                                "description": "Whether to perform case-sensitive search.",
                                "default": False,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute an approved terminal shell command in the project root.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Command string to run (e.g. 'python -m pytest tests/').",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Timeout in seconds (default: 30).",
                                "default": 30,
                            },
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_tests",
                    "description": "Run the project test suite or a specific test file using pytest.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "test_target": {
                                "type": "string",
                                "description": "Optional specific test path or test file.",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_status",
                    "description": "Get git status and list of modified or untracked files.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_diff",
                    "description": "Inspect uncommitted git diff in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Optional specific file path for diff.",
                            },
                        },
                        "required": [],
                    },
                },
            },
        ]

    def get_system_prompt_tools_doc(self) -> str:
        """Return a formatted markdown documentation of available tools for system prompt."""
        docs = [
            "You have access to real workspace tools. When you need to inspect or modify the code, execute a tool call.",
            "Always inspect the codebase before making assumptions or editing files.",
            "",
            "Available tools:",
            "- `list_dir(path='.')`: List files and subdirectories.",
            "- `read_file(path, start_line=None, end_line=None)`: Read file contents with line numbers.",
            "- `write_file(path, content)`: Create or overwrite a file.",
            "- `edit_file(path, old_string, new_string)`: Replace exact unique text in a file.",
            "- `grep_search(query, path='.')`: Search for text patterns across project files.",
            "- `run_command(command, timeout=30)`: Run approved shell commands (e.g. `pip check`).",
            "- `run_tests(test_target=None)`: Run project pytest suite and report actual test outcomes.",
            "- `git_status()`: Inspect modified files and repository status.",
            "- `git_diff(path=None)`: Review git diffs of uncommitted changes.",
            "",
            "To call a tool, either use native tool calling or output:",
            "<tool_call>",
            '{"name": "tool_name", "arguments": {"arg1": "val1"}}',
            "</tool_call>",
        ]
        return "\n".join(docs)

    # -------------------------------------------------------------------------
    # Tool Execution Dispatcher
    # -------------------------------------------------------------------------

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """Validate and dispatch a tool call by name.
        
        Args:
            name: Tool function name
            arguments: Dict of keyword arguments
            
        Returns:
            ToolExecutionResult
        """
        handlers = {
            "list_dir": self.tool_list_dir,
            "read_file": self.tool_read_file,
            "write_file": self.tool_write_file,
            "edit_file": self.tool_edit_file,
            "grep_search": self.tool_grep_search,
            "run_command": self.tool_run_command,
            "run_tests": self.tool_run_tests,
            "git_status": self.tool_git_status,
            "git_diff": self.tool_git_diff,
        }
        
        handler = handlers.get(name)
        if not handler:
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                output="",
                error=f"Unknown tool: '{name}'. Available tools: {list(handlers.keys())}",
            )
            
        try:
            return await handler(**arguments)
        except TypeError as e:
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                output="",
                error=f"Invalid arguments for {name}: {str(e)}",
            )
        except Exception as e:
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                output="",
                error=f"Tool execution failed: {str(e)}",
            )

    # -------------------------------------------------------------------------
    # Individual Tool Implementations
    # -------------------------------------------------------------------------

    async def tool_list_dir(self, path: str = ".", max_depth: int = 2) -> ToolExecutionResult:
        """List files and directories within path."""
        valid, resolved, reason = self.path_validator.validate_read(path)
        if not valid:
            return ToolExecutionResult("list_dir", False, "", error=reason)
            
        if not os.path.isdir(resolved):
            return ToolExecutionResult("list_dir", False, "", error=f"Not a directory: {path}")

        lines = []
        base_path = Path(resolved)
        project_base = Path(self.project_root)

        # Ignore noisy / hidden directories
        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".freebuff"}

        try:
            for root, dirs, files in os.walk(resolved):
                # Filter out ignored dirs
                dirs[:] = [d for d in dirs if d not in ignored]
                
                rel_root = os.path.relpath(root, resolved)
                depth = 0 if rel_root == "." else len(Path(rel_root).parts)
                if depth >= max_depth:
                    dirs.clear()
                    continue
                    
                indent = "  " * depth
                folder_name = os.path.basename(root) or "."
                if folder_name != ".":
                    lines.append(f"{indent}[dir] {folder_name}/")
                    
                for f in sorted(files):
                    file_indent = "  " * (depth + (0 if folder_name == "." else 1))
                    lines.append(f"{file_indent}{f}")
                    
            output = "\n".join(lines[:100])
            if len(lines) > 100:
                output += f"\n... [truncated, {len(lines) - 100} more items]"
                
            return ToolExecutionResult("list_dir", True, output or "(empty directory)")
        except Exception as e:
            return ToolExecutionResult("list_dir", False, "", error=str(e))

    async def tool_read_file(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> ToolExecutionResult:
        """Read a file with 1-indexed line numbers."""
        valid, content, msg = self.filesystem_tools.read_file(path)
        if not valid or content is None:
            return ToolExecutionResult("read_file", False, "", error=msg or f"Failed to read {path}")

        file_lines = content.splitlines()
        total_lines = len(file_lines)

        start = max(1, start_line) if start_line is not None else 1
        end = min(total_lines, end_line) if end_line is not None else min(total_lines, start + 300)

        formatted_lines = []
        for idx in range(start - 1, end):
            formatted_lines.append(f"{idx + 1:4d} | {file_lines[idx]}")

        header = f"File: {path} (lines {start}-{end} of {total_lines})\n"
        output = header + "\n".join(formatted_lines)
        return ToolExecutionResult("read_file", True, output, data={"total_lines": total_lines})

    async def tool_write_file(self, path: str, content: str) -> ToolExecutionResult:
        """Create or overwrite a file with approval and path validation."""
        valid, resolved, reason = self.path_validator.validate_write(path)
        if not valid:
            return ToolExecutionResult("write_file", False, "", error=reason)

        is_new = not os.path.exists(resolved)
        action_name = "create_file" if is_new else "overwrite_file"

        # Check approval callback
        if self.approval_callback:
            approved = self.approval_callback(action_name, {"path": path, "is_new": is_new})
            if not approved:
                return ToolExecutionResult(
                    "write_file",
                    False,
                    "",
                    error=f"Operation cancelled by user: write to '{path}' was not approved.",
                    approval_required=True,
                )

        success, msg = self.filesystem_tools.write_file(path, content, create_backup=True)
        if success:
            if path not in self.changed_files:
                self.changed_files.append(path)
            return ToolExecutionResult("write_file", True, f"Successfully wrote {len(content)} bytes to {path}")
        return ToolExecutionResult("write_file", False, "", error=msg)

    async def tool_edit_file(
        self,
        path: str,
        old_string: Optional[str] = None,
        new_string: Optional[str] = None,
        target_text: Optional[str] = None,
        replacement_text: Optional[str] = None,
    ) -> ToolExecutionResult:
        """Edit an existing file by replacing a unique occurrence of old_string."""
        target = old_string if old_string is not None else target_text
        replacement = new_string if new_string is not None else replacement_text
        if target is None or replacement is None:
            return ToolExecutionResult(
                "edit_file",
                False,
                "",
                error="Both target text (old_string) and replacement text (new_string) must be provided.",
            )

        valid, resolved, reason = self.path_validator.validate_write(path)
        if not valid:
            return ToolExecutionResult("edit_file", False, "", error=reason)

        if not os.path.exists(resolved):
            return ToolExecutionResult("edit_file", False, "", error=f"File does not exist: {path}")

        valid_read, current_content, msg = self.filesystem_tools.read_file(path)
        if not valid_read or current_content is None:
            return ToolExecutionResult("edit_file", False, "", error=f"Could not read {path}: {msg}")

        occurrences = current_content.count(target)
        if occurrences == 0:
            return ToolExecutionResult(
                "edit_file",
                False,
                "",
                error=f"Target text not found in {path}. Make sure whitespace and line breaks match exactly.",
            )
        if occurrences > 1:
            return ToolExecutionResult(
                "edit_file",
                False,
                "",
                error=f"Target text found {occurrences} times in {path}. Please provide a larger unique context block.",
            )

        # Check approval callback
        if self.approval_callback:
            approved = self.approval_callback("edit_file", {"path": path})
            if not approved:
                return ToolExecutionResult(
                    "edit_file",
                    False,
                    "",
                    error=f"Operation cancelled by user: edit to '{path}' was not approved.",
                    approval_required=True,
                )

        updated_content = current_content.replace(target, replacement, 1)
        success, write_msg = self.filesystem_tools.write_file(path, updated_content, create_backup=True)

        if success:
            if path not in self.changed_files:
                self.changed_files.append(path)
            return ToolExecutionResult("edit_file", True, f"Successfully edited {path} (1 replacement made)")
        return ToolExecutionResult("edit_file", False, "", error=write_msg)

    async def tool_grep_search(
        self,
        query: str,
        path: str = ".",
        case_sensitive: bool = False,
    ) -> ToolExecutionResult:
        """Search across files for matching lines."""
        valid, resolved, reason = self.path_validator.validate_read(path)
        if not valid:
            return ToolExecutionResult("grep_search", False, "", error=reason)

        results = []
        pattern_flags = 0 if case_sensitive else re.IGNORECASE
        try:
            compiled_regex = re.compile(query, pattern_flags)
        except re.error as e:
            return ToolExecutionResult("grep_search", False, "", error=f"Invalid regex: {e}")

        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".freebuff"}

        try:
            target_files = []
            if os.path.isfile(resolved):
                target_files.append(resolved)
            else:
                for root, dirs, files in os.walk(resolved):
                    dirs[:] = [d for d in dirs if d not in ignored]
                    for f in files:
                        if not f.endswith((".pyc", ".png", ".jpg", ".exe", ".bin", ".whl")):
                            target_files.append(os.path.join(root, f))
                            if len(target_files) >= 200:
                                break

            for file_path in target_files:
                try:
                    rel = os.path.relpath(file_path, self.project_root)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for lineno, line in enumerate(f, 1):
                            if compiled_regex.search(line):
                                results.append(f"{rel}:{lineno}: {line.strip()[:150]}")
                                if len(results) >= 50:
                                    break
                except Exception:
                    continue
                if len(results) >= 50:
                    break

            if not results:
                return ToolExecutionResult("grep_search", True, f"No matches found for '{query}' in {path}")
            
            output = "\n".join(results)
            return ToolExecutionResult("grep_search", True, output, data={"count": len(results)})
        except Exception as e:
            return ToolExecutionResult("grep_search", False, "", error=str(e))

    async def tool_run_command(self, command: str, timeout: int = 30) -> ToolExecutionResult:
        """Run an approved shell command safely in project root."""
        # Security validation
        is_safe, reason = self.command_validator.validate(command, self.project_root, self.project_root)
        if not is_safe:
            return ToolExecutionResult(
                "run_command",
                False,
                "",
                error=f"Command blocked by security policy: {reason}",
            )

        # Approval check
        if self.approval_callback:
            approved = self.approval_callback("run_command", {"command": command})
            if not approved:
                return ToolExecutionResult(
                    "run_command",
                    False,
                    "",
                    error=f"Command cancelled: execution of '{command}' was rejected by user.",
                    approval_required=True,
                )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out_str = stdout.decode("utf-8", errors="replace")
            err_str = stderr.decode("utf-8", errors="replace")
            exit_code = proc.returncode

            combined = out_str
            if err_str:
                combined += f"\n[stderr]\n{err_str}" if combined else err_str

            success = (exit_code == 0)
            self.commands_executed.append({
                "command": command,
                "exit_code": exit_code,
                "success": success,
            })

            return ToolExecutionResult(
                "run_command",
                success,
                combined or "(Command produced no output)",
                error=err_str if not success else None,
                data={"exit_code": exit_code},
            )
        except asyncio.TimeoutError:
            return ToolExecutionResult(
                "run_command",
                False,
                "",
                error=f"Command timed out after {timeout} seconds",
            )
        except Exception as e:
            return ToolExecutionResult(
                "run_command",
                False,
                "",
                error=f"Failed to execute command: {str(e)}",
            )

    async def tool_run_tests(
        self,
        test_target: Optional[str] = None,
        path: Optional[str] = None,
        target: Optional[str] = None,
    ) -> ToolExecutionResult:
        """Run pytest test suite on the project and parse results."""
        actual_target = test_target or path or target
        cmd = [sys.executable, "-m", "pytest"]
        if actual_target:
            cmd.append(actual_target)
        cmd_str = " ".join(cmd)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            out_str = stdout.decode("utf-8", errors="replace")
            err_str = stderr.decode("utf-8", errors="replace")
            exit_code = proc.returncode

            # Extract summary line (e.g. "53 passed in 0.86s")
            summary = "Tests completed."
            for line in reversed(out_str.splitlines()):
                if "passed" in line or "failed" in line or "error" in line:
                    summary = line.strip("= ")
                    break

            success = (exit_code == 0)
            self.tests_executed.append({
                "target": test_target or "all",
                "exit_code": exit_code,
                "summary": summary,
                "success": success,
            })

            full_output = out_str + (f"\n{err_str}" if err_str else "")
            return ToolExecutionResult(
                "run_tests",
                success,
                full_output,
                error=None if success else f"Tests failed with exit code {exit_code}",
                data={"exit_code": exit_code, "summary": summary},
            )
        except asyncio.TimeoutError:
            return ToolExecutionResult("run_tests", False, "", error="Tests timed out after 60 seconds")
        except Exception as e:
            return ToolExecutionResult("run_tests", False, "", error=str(e))

    async def tool_git_status(self) -> ToolExecutionResult:
        """Inspect Git repository status."""
        try:
            res = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                output = res.stdout.strip() or "(working tree clean)"
                return ToolExecutionResult("git_status", True, output)
            return ToolExecutionResult("git_status", False, "", error=res.stderr)
        except Exception as e:
            return ToolExecutionResult("git_status", False, "", error=str(e))

    async def tool_git_diff(self, path: Optional[str] = None) -> ToolExecutionResult:
        """Inspect Git diff."""
        cmd = ["git", "diff"]
        if path:
            cmd.extend(["--", path])
        try:
            res = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                output = res.stdout.strip() or "(no uncommitted diff)"
                return ToolExecutionResult("git_diff", True, output)
            return ToolExecutionResult("git_diff", False, "", error=res.stderr)
        except Exception as e:
            return ToolExecutionResult("git_diff", False, "", error=str(e))
