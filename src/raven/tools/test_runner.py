"""Test Runner - test execution and result parsing."""

from __future__ import annotations

import asyncio
import subprocess
import json
from typing import Dict, Any, List, Optional
import tempfile
import os


class TestRunner:
    """Test execution and result parsing for RAVEN agent workflows."""
    
    def __init__(self, timeout: int = 60, project_root: Optional[str] = None):
        """Initialize the test runner.
        
        Args:
            timeout: Default timeout for test execution in seconds
            project_root: Optional project root directory
        """
        self.timeout = timeout
        self.project_root = os.path.abspath(project_root) if project_root else None
    
    async def run_pytest(self, 
                         test_path: Optional[str] = None,
                         args: Optional[List[str]] = None) -> dict:
        """Run pytest and capture results.
        
        Args:
            test_path: Path to test files (defaults to current directory)
            args: Additional pytest arguments
            
        Returns:
            Dict with test execution results
        """
        if self.project_root:
            test_path = test_path or self.project_root
            cmd = ["pytest", "-v", "--tb=short"]
            if args:
                cmd.extend(args)
        else:
            test_path = test_path or "."
            cmd = ["pytest", "-v", "--tb=short"]
            if args:
                cmd.extend(args)
        
        return await self._run_test(test_path, cmd)
    
    async def run_unittest(self, 
                           test_path: Optional[str] = None,
                           args: Optional[List[str]] = None) -> dict:
        """Run unittest and capture results.
        
        Args:
            test_path: Path to test files
            args: Additional unittest arguments
            
        Returns:
            Dict with test execution results
        """
        test_path = test_path or "."
        cmd = ["python", "-m", "unittest", test_path]
        if args:
            cmd.extend(args)
        
        return await self._run_test(test_path, cmd)
    
    async def _run_test(self, test_path: str, cmd: List[str]) -> dict:
        """Run tests and capture structured results."""
        full_cmd = cmd + [test_path]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "exit_code": -1,
                    "timed_out": True,
                    "stdout": "",
                    "stderr": "Test execution timed out",
                    "passed": 0,
                    "failed": 0,
                    "errored": 0,
                }
            
            output = stdout.decode(errors="replace")
            errors_output = stderr.decode(errors="replace")
            
            # Parse pytest/unittest output to count results
            result = self._parse_test_output(output, errors_output)
            result["exit_code"] = proc.returncode if proc.returncode is not None else -1
            result["timed_out"] = False
            result["stdout"] = output
            result["stderr"] = errors_output
            
            return result
            
        except FileNotFoundError:
            return {
                "exit_code": -1,
                "timed_out": False,
                "stdout": "",
                "stderr": "pytest/unittest not found",
                "passed": 0,
                "failed": 0,
                "errored": 0,
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "timed_out": False,
                "stdout": "",
                "stderr": str(e),
                "passed": 0,
                "failed": 0,
                "errored": 0,
            }
    
    @staticmethod
    def _parse_test_output(stdout: str, stderr: str) -> dict:
        """Parse test output to extract pass/fail counts."""
        passed = 0
        failed = 0
        errored = 0
        
        # Parse pytest output formats
        # Format: "= passing =12, failing =3, skipping =2"
        import re
        
        # Look for passing count
        match = re.search(r'passing\s*=\s*(\d+)', stdout + stderr)
        if match:
            passed = int(match.group(1))
        
        # Look for failing count
        match = re.search(r'failing\s*=\s*(\d+)', stdout + stderr)
        if match:
            failed = int(match.group(1))
        
        # Look for errored count
        match = re.search(r'errored\s*=\s*(\d+)', stdout + stderr)
        if match:
            errored = int(match.group(1))
        
        # If not found in pytest format, look for summary lines
        if passed == 0 and failed == 0:
            # Count test function results
            passed = len(re.findall(r'PASSED', stdout + stderr))
            failed = len(re.findall(r'FAILED', stdout + stderr))
            errored = len(re.findall(r'ERROR', stdout + stderr))
        
        return {
            "passed": passed,
            "failed": failed,
            "errored": errored,
            "total": passed + failed + errored,
        }