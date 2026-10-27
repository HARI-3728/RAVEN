"""Coding Agent - core execution loop connecting model reasoning to real workspace tools.

Implements Section 7 of RAVEN Specification:
1. Context assembly (workspace, git status, tools)
2. Model invocation with capabilities
3. Tool call parsing (native or text fallback)
4. Validation and permission checks
5. Controlled tool execution
6. Structured tool result feed-back
7. Iteration control, timeouts, and cancellation
8. Final outcome verification and reporting
"""

from __future__ import annotations

import os
import sys
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable

from ..providers.base import AIProvider, ProviderResult
from ..tools.coding_tools import CodingTools, ToolExecutionResult
from ..tools.tool_parser import parse_tool_calls_from_text, clean_content_after_tool_extraction


class AgentTaskReport:
    """Summary report of an agent coding session."""
    
    def __init__(self, task: str):
        self.task = task
        self.summary: str = ""
        self.changed_files: List[str] = []
        self.tools_executed: List[Dict[str, Any]] = []
        self.commands_run: List[Dict[str, Any]] = []
        self.tests_run: List[Dict[str, Any]] = []
        self.tool_calls_count: int = 0
        self.iterations: int = 0
        self.success: bool = False
        self.error: Optional[str] = None
        self.duration_seconds: float = 0.0

    @property
    def files_changed(self) -> List[str]:
        return self.changed_files

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "summary": self.summary,
            "changed_files": self.changed_files,
            "tools_executed": self.tools_executed,
            "commands_run": self.commands_run,
            "tests_run": self.tests_run,
            "tool_calls_count": self.tool_calls_count,
            "iterations": self.iterations,
            "success": self.success,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }


class CodingAgent:
    """Autonomous coding agent that inspects code, edits files, and runs tests."""

    def __init__(
        self,
        provider: AIProvider,
        project_root: str,
        model: Optional[str] = None,
        max_iterations: int = 25,
        on_thought: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_result: Optional[Callable[[str, ToolExecutionResult], None]] = None,
        on_approval_required: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        """Initialize the coding agent.
        
        Args:
            provider: Configured AIProvider instance
            project_root: Path to project root
            model: Optional model identifier
            max_iterations: Maximum tool-execution iterations before stopping
            on_thought: Callback when model produces text / reasoning
            on_tool_call: Callback when a tool is called
            on_tool_result: Callback when a tool finishes execution
            on_approval_required: Callback for asking user approval
        """
        self.provider = provider
        self.project_root = os.path.abspath(project_root)
        self.model = model or getattr(provider, "default_model", "gpt-4o")
        self.max_iterations = max_iterations
        
        self.on_thought = on_thought
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.on_approval_required = on_approval_required

        # Initialize real workspace tools with approval callback
        self.tools = CodingTools(
            project_root=self.project_root,
            approval_callback=self.on_approval_required,
        )

        # Multi-turn conversation history
        self.messages: List[Dict[str, Any]] = []
        self._cancellation_event: asyncio.Event = asyncio.Event()

    def cancel(self) -> None:
        """Cancel current execution loop."""
        self._cancellation_event.set()

    def reset_history(self) -> None:
        """Clear conversation history."""
        self.messages.clear()
        self._cancellation_event.clear()

    async def execute_task(self, user_task: str) -> AgentTaskReport:
        """Run the complete agent loop for a user coding request.
        
        Args:
            user_task: Natural-language request (e.g. "Fix the failing test in auth")
            
        Returns:
            AgentTaskReport with final results, changed files, and test outcomes
        """
        self._cancellation_event.clear()
        start_time = time.time()
        report = AgentTaskReport(user_task)

        # 1. Build initial workspace context
        system_prompt = self._build_system_prompt()

        if not self.messages:
            self.messages.append({"role": "system", "content": system_prompt})

        self.messages.append({"role": "user", "content": user_task})

        tool_definitions = self.tools.get_tool_definitions()
        iteration = 0

        while iteration < self.max_iterations:
            if self._cancellation_event.is_set():
                report.error = "Task cancelled by user."
                break

            iteration += 1
            report.iterations = iteration

            # Build prompt payload
            prompt_text = self._format_messages_for_prompt()

            # Call provider
            try:
                result = await self.provider.generate_response(
                    prompt=prompt_text,
                    context=f"Project root: {self.project_root}",
                    model=self.model,
                )
            except Exception as e:
                report.error = f"Model provider error: {str(e)}"
                break

            if not result.success and result.error:
                report.error = f"Provider error: {result.error}"
                break

            raw_content = result.content or ""

            # Check for tool calls (native or parsed from content)
            tool_calls = getattr(result, "tool_calls", None) or []
            if not tool_calls:
                tool_calls = parse_tool_calls_from_text(raw_content)

            # If the model produced thought/explanation text
            thought_text = clean_content_after_tool_extraction(raw_content)
            if thought_text and self.on_thought:
                self.on_thought(thought_text)

            # Append assistant message to history
            self.messages.append({"role": "assistant", "content": raw_content})

            # If no tool calls requested, the model has finished its task!
            if not tool_calls:
                report.summary = thought_text or raw_content
                report.success = True
                break

            # Process all requested tool calls in this turn
            for call in tool_calls:
                if self._cancellation_event.is_set():
                    break

                tool_name = call.get("name", "")
                tool_args = call.get("arguments", {})
                call_id = call.get("id", f"call_{iteration}")

                report.tool_calls_count += 1

                # Notify listener
                if self.on_tool_call:
                    self.on_tool_call(tool_name, tool_args)

                # Execute tool
                tool_result = await self.tools.execute_tool(tool_name, tool_args)
                report.tools_executed.append({
                    "name": tool_name,
                    "arguments": tool_args,
                    "success": tool_result.success,
                })

                # Notify listener
                if self.on_tool_result:
                    self.on_tool_result(tool_name, tool_result)

                # Format tool output for next turn
                result_content = (
                    f"Tool: {tool_name}\n"
                    f"Success: {tool_result.success}\n"
                    f"Output:\n{tool_result.output}"
                )
                if tool_result.error:
                    result_content += f"\nError: {tool_result.error}"

                # Append tool result to conversation history
                self.messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "tool_call_id": call_id,
                    "content": result_content,
                })

        # Final outcome summary
        report.duration_seconds = round(time.time() - start_time, 2)
        report.changed_files = list(self.tools.changed_files)
        report.commands_run = list(self.tools.commands_executed)
        report.tests_run = list(self.tools.tests_executed)

        if iteration >= self.max_iterations and not report.summary:
            report.success = False
            report.error = f"Iteration limit reached ({self.max_iterations})."
            report.summary = f"Reached maximum allowed iterations ({self.max_iterations})."

        return report

    def _build_system_prompt(self) -> str:
        """Construct comprehensive system instructions for the coding agent."""
        return (
            "You are RAVEN, an elite terminal AI coding engineer operating directly in the user's workspace.\n"
            f"Active Workspace: {self.project_root}\n\n"
            "Your workflow:\n"
            "1. Inspect the codebase first using `list_dir`, `read_file`, or `grep_search`. Do not guess.\n"
            "2. Plan necessary modifications and explain your thinking concisely.\n"
            "3. Make precise edits using `edit_file` or `write_file`.\n"
            "4. Verify your changes by running tests with `run_tests` or commands with `run_command`.\n"
            "5. If tests or commands fail, diagnose the root cause and apply a fix.\n"
            "6. When complete, provide a concise summary of files changed, checks run, and outcomes.\n\n"
            f"{self.tools.get_system_prompt_tools_doc()}\n"
        )

    def _format_messages_for_prompt(self) -> str:
        """Format message conversation history into a unified model prompt."""
        formatted_parts = []
        for msg in self.messages:
            role = msg.get("role", "").capitalize()
            content = msg.get("content", "")
            if role == "Tool":
                tool_name = msg.get("name", "Tool")
                formatted_parts.append(f"[Tool Result for {tool_name}]:\n{content}")
            elif role == "System":
                formatted_parts.append(f"System:\n{content}")
            elif role == "User":
                formatted_parts.append(f"User: {content}")
            elif role == "Assistant":
                formatted_parts.append(f"Assistant:\n{content}")

        return "\n\n---\n\n".join(formatted_parts)
