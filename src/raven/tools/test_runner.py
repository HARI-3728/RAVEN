"""Test Runner - permitted test execution with mocked providers and proper boundaries.

Provides controlled test execution with:
- Mocked AI providers for deterministic testing
- Project file boundaries
- Approved command validation
- Test isolation between runs
- Context sharing support
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple

from ..security.command_validator import CommandValidator
from .filesystem import FileSystemTools
from .git_tools import GitTools


class TestRunner:
    """Runs tests with mocked providers and proper boundaries.
    
    Key features:
    - Mocked AI providers for deterministic testing (no paid API keys needed)
    - Project file boundary enforcement
    - Approved command validation
    - Test isolation and cleanup
    - Context sharing support
    - Controlled test execution environment
    """
    
    def __init__(
        self,
        project_root: str,
        command_validator: Optional[CommandValidator] = None,
        filesystem_tools: Optional[FileSystemTools] = None,
    ):
        """Initialize the TestRunner.
        
        Args:
            project_root: Project root directory for test execution boundaries
            command_validator: Optional CommandValidator instance
            filesystem_tools: Optional FileSystemTools instance
        """
        self.project_root = os.path.abspath(project_root)
        self.command_validator = command_validator or CommandValidator()
        self.filesystem_tools = filesystem_tools or FileSystemTools(project_root)
        self._temp_dirs: List[str] = []
        self._test_results: List[dict] = []
    
    async def run_mocked_test(
        self,
        test_name: str,
        test_code: str,
        provider_configs: Optional[List[dict]] = None,
    ) -> dict:
        """Run a test with mocked AI providers for deterministic results.
        
        This is the primary test method that does NOT require paid API keys.
        All provider calls are mocked to return deterministic responses.
        
        Args:
            test_name: Name/identifier for this test
            test_code: Python code to execute as the test (should use test infrastructure)
            provider_configs: Optional provider configurations for mocking
            
        Returns:
            dict with test results including success, output, errors, etc.
        """
        result = {
            "name": test_name,
            "success": False,
            "output": "",
            "errors": [],
            "provider_calls": 0,
            "execution_time": 0,
        }
        
        start_time = asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0
        
        try:
            # Create a temporary test directory with .env file
            with tempfile.TemporaryDirectory() as tmpdir:
                # Set up mock environment
                env = os.environ.copy()
                
                # Set up mock API keys in environment for the test
                if provider_configs:
                    for pc in provider_configs:
                        env_name = pc.get("api_key_env", "")
                        env_value = pc.get("mock_key", "sk-mock-test-key-12345abcdef")
                        if env_name:
                            env[env_name] = env_value
                
                # Execute the test code in isolated environment
                # Wrap with test infrastructure
                wrapped_code = self._wrap_test_code(test_code, tmpdir, env)
                
                # Execute
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-c", wrapped_code,
                    cwd=tmpdir,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=30
                )
                
                execution_time = asyncio.get_event_loop().time() - start_time
                result["output"] = stdout.decode("utf-8", errors="replace")
                result["errors"] = stderr.decode("utf-8", errors="replace") if stderr else ""
                result["execution_time"] = execution_time
                result["provider_calls"] = self._count_mock_provider_calls(stdout, stderr)
                
                # Consider test successful if no errors and exit code 0
                result["success"] = process.returncode == 0 and not result["errors"]
                
        except asyncio.TimeoutError:
            result["errors"].append("Test timed out after 30 seconds")
            result["execution_time"] = 30
        except Exception as e:
            result["errors"].append(str(e))
            result["execution_time"] = asyncio.get_event_loop().time() - start_time
        
        return result
    
    def _wrap_test_code(self, test_code: str, tmpdir: str, env: dict) -> str:
        """Wrap test code with test infrastructure.
        
        Args:
            test_code: The original test code
            tmpdir: Temporary test directory
            env: Environment variables
            
        Returns:
            Wrapped code string
        """
        # Import raven test modules and set up mocking
        wrapper = f'''
import sys
import os

# Set up mock environment for RAVEN providers
os.environ["RAVEN_TEST_MODE"] = "true"

# Set mock API keys from provider configs
{self._set_mock_env_vars("")}

# Mock the provider modules to return deterministic results
sys.path.insert(0, "{os.path.dirname(os.path.abspath(__file__))}/../..")
sys.path.insert(0, "{os.path.dirname(os.path.abspath(__file__))}/../src")

# Import raven modules
from raven.providers.base import AIProvider, ProviderResult
from raven.providers.registry import ProviderRegistry
from raven.providers.openai_provider import OpenAIProvider
from raven.providers.anthropic_provider import AnthropicProvider  
from raven.providers.gemini_provider import GeminiProvider
from raven.providers.local_provider import LocalProvider
from raven.agents.role_manager import RoleManager
from raven.agents.agent_factory import AgentFactory

# Set up mock provider instances
registry = ProviderRegistry()

# Mock OpenAI provider
class MockOpenAIProvider(OpenAIProvider):
    async def _generate_response_core(self, prompt, context, model_id):
        return ProviderResult(
            content=f"[MOCKED OPENAI {{model_id}}]: {{prompt[:50]}}...",
            model=model_id,
            provider="openai",
            usage={{"prompt_tokens": len(prompt.split()), "completion_tokens": 50}},
            finish_reason="stop",
        )

mock_openai = MockOpenAIProvider({{
    "api_key_env": "OPENAI_API_KEY",
    "default_model": "gpt-4o",
    "supported_models": ["gpt-4o", "gpt-3.5-turbo"],
    "timeout": 30,
    "max_retries": 2,
}})
registry.register("openai", MockOpenAIProvider)

# Mock Anthropic provider  
class MockAnthropicProvider(AnthropicProvider):
    async def _generate_response_core(self, prompt, context, model_id):
        return ProviderResult(
            content=f"[MOCKED ANTHROPIC {{model_id}}]: Analysis of: {{prompt[:50]}}...",
            model=model_id,
            provider="anthropic",
            usage={{"prompt_tokens": len(prompt.split()), "completion_tokens": 40}},
            finish_reason="stop",
        )

mock_anthropic = MockAnthropicProvider({{
    "api_key_env": "ANTHROPIC_API_KEY",
    "default_model": "claude-3-sonnet-20240229",
    "supported_models": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "timeout": 30,
    "max_retries": 2,
}})
registry.register("anthropic", mock_anthropic)

# Mock Gemini provider
class MockGeminiProvider(GeminiProvider):
    async def _generate_response_core(self, prompt, context, model_id):
        return ProviderResult(
            content=f"[MOCKED GEMINI {{model_id}}]: Response to: {{prompt[:50]}}...",
            model=model_id,
            provider="gemini",
            usage={{"prompt_tokens": len(prompt.split()), "completion_tokens": 30}},
            finish_reason="stop",
        )

mock_gemini = MockGeminiProvider({{
    "api_key_env": "GEMINI_API_KEY",
    "default_model": "gemini-1.5-flash",
    "supported_models": ["gemini-1.5-flash", "gemini-1.5-pro"],
    "timeout": 30,
    "max_retries": 2,
}})
registry.register("gemini", mock_gemini)

# Mock Local provider (Ollama)
class MockLocalProvider(LocalProvider):
    async def _check_model_available(self, model_id):
        return True  # Assume all models available

    async def _call_local_model(self, prompt, model_id):
        return ProviderResult(
            content=f"[MOCKED LOCAL {{model_id}}]: Processed: {{prompt[:50]}}...",
            model=model_id,
            provider="local",
            usage={{"prompt_tokens": len(prompt.split()), "completion_tokens": 35}},
            finish_reason="stop",
        )

mock_local = MockLocalProvider({{
    "default_model": "codellama:34b",
    "supported_models": ["codellama:34b", "llama3:8b"],
    "timeout": 60,
    "max_retries": 3,
    "ollama_base_url": "http://localhost:11434",
}})
registry.register("local", mock_local)

# Set up role manager
role_manager = RoleManager()

# Set up agent factory
factory = AgentFactory(role_manager=role_manager, provider_registry=registry)

# Set RAVEN project root
os.environ["RAVEN_PROJECT_ROOT"] = "{tmpdir}"

# Now execute the test code
{test_code}
'''
        return wrapper
    
    def _set_mock_env_vars(self, prefix: str) -> str:
        """Set mock environment variables for providers.
        
        Args:
            prefix: Variable name prefix
            
        Returns:
            Python code to set env vars
        """
        lines = []
        lines.append("os.environ['RAVEN_TEST_MODE'] = 'true'")
        lines.append("os.environ['OPENAI_API_KEY'] = 'sk-mock-test-key-openai'")
        lines.append("os.environ['ANTHROPIC_API_KEY'] = 'sk-mock-test-key-anthropic'")
        lines.append("os.environ['GEMINI_API_KEY'] = 'sk-mock-test-key-gemini'")
        lines.append("os.environ['OPENAI_COMPATIBLE_API_KEY'] = 'sk-mock-test-key-compatible'")
        return "\n".join(lines)
    
    def _count_mock_provider_calls(self, stdout: str, stderr: str) -> int:
        """Count mocked provider calls in test output.
        
        Args:
            stdout: Standard output
            stderr: Standard error
            
        Returns:
            Number of mock provider calls detected
        """
        count = 0
        # Look for mock provider call patterns
        patterns = [
            r"MOCKED OPENAI",
            r"MOCKED ANTHROPIC", 
            r"MOCKED GEMINI",
            r"MOCKED LOCAL",
        ]
        for pattern in patterns:
            matches = len(re.findall(pattern, stdout + stderr))
            count += matches
        return count
    
    async def run_approved_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30,
    ) -> dict:
        """Run a command with approval validation.
        
        Only commands that pass the command validator are allowed.
        Prevents path traversal and dangerous operations.
        
        Args:
            command: Command string to execute
            cwd: Working directory (defaults to project_root)
            timeout: Command timeout in seconds
            
        Returns:
            dict with execution results
        """
        cwd = cwd or self.project_root
        
        # Validate the command
        is_valid, reason = self.command_validator.validate(
            command, cwd, self.project_root
        )
        
        if not is_valid:
            return {
                "approved": False,
                "cancelled": True,
                "error": f"Command rejected: {reason}",
                "exit_code": -1,
                "stdout": "",
                "stderr": "",
            }
        
        try:
            process = await asyncio.create_subprocess_exec(
                *self._parse_command(command),
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            return {
                "approved": True,
                "cancelled": False,
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except asyncio.TimeoutError:
            return {
                "approved": True,
                "cancelled": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out",
            }
        except Exception as e:
            return {
                "approved": True,
                "cancelled": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }
    
    def _parse_command(self, command: str) -> List[str]:
        """Parse a command string into a list suitable for subprocess.
        
        Args:
            command: Command string
            
        Returns:
            List of arguments for subprocess
        """
        # Simple parsing - split by spaces
        # In production, would use shlex.split for proper handling
        return command.split()
    
    def get_test_capabilities(self) -> dict:
        """Get the test execution capabilities and limitations.
        
        Returns:
            dict with capabilities information
        """
        return {
            "mocked_providers": True,
            "requires_api_keys": False,
            "max_test_duration": 30,
            "supported_providers": ["openai", "anthropic", "gemini", "local"],
            "file_boundaries": True,
            "command_validation": True,
            "isolation": True,
        }