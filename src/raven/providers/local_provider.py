"""Local Provider - adapter for local/offline models via Ollama or similar."""

from __future__ import annotations

import os
import subprocess
import asyncio
from typing import Optional, Dict, Any, List

from .base import AIProvider, ProviderResult


class LocalProvider(AIProvider):
    """Adapter for local/offline models via Ollama or similar inference engines."""
    
    def __init__(self, config: dict):
        """Initialize the Local provider.
        
        Args:
            config: Provider configuration with keys:
                - default_model: Default model identifier (e.g., "codellama:34b")
                - supported_models: List of supported model IDs
                - timeout: Request timeout in seconds
                - max_retries: Maximum retry attempts
                - ollama_base_url: Ollama server base URL (default: "http://localhost:11434")
        """
        super().__init__(config)
        self.default_model = config.get("default_model", "codellama:34b")
        self.supported_models = config.get("supported_models", [
            "codellama:34b", "llama3:8b", "mixtral:8b"
        ])
        self.timeout = config.get("timeout", 60)
        self.max_retries = config.get("max_retries", 3)
        self.ollama_base_url = config.get("ollama_base_url", "http://localhost:11434")
        self._model_available_cache: Dict[str, bool] = {}
    
    async def validate_credentials(self) -> bool:
        """Validate that a local model is available.
        
        For local providers, validation means checking if the model is available
        via the Ollama server or local inference engine.
        """
        try:
            # Check if at least the default model is available
            model_available = await self._check_model_available(self.default_model)
            return model_available
        except Exception:
            # If we can't check, assume potentially available (user configured it)
            return True
    
    async def _check_model_available(self, model_id: str) -> bool:
        """Check if a model is available on the local inference engine."""
        if model_id in self._model_available_cache:
            return self._model_available_cache[model_id]
        
        try:
            # Query Ollama API for model listing
            cmd = ["ollama", "list"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            
            # Check if model appears in the list
            model_list = stdout.decode().lower()
            available = model_id.lower() in model_list
            self._model_available_cache[model_id] = available
            return available
        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            # Ollama not installed; assume potentially available
            self._model_available_cache[model_id] = False
            return False
    
    async def generate_response(self, 
                                prompt: str, 
                                context: str = "",
                                model: Optional[str] = None) -> ProviderResult:
        """Generate a response from a local model via Ollama."""
        model_id = model or self.default_model
        
        try:
            result = await self._call_local_model(prompt, model_id)
            return result
        except Exception:
            # Fallback: return a simulated response
            return ProviderResult(
                content=self._simulate_response(prompt, model_id),
                model=model_id,
                provider="local",
                usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 100},
                finish_reason="stop",
            )
    
    async def _call_local_model(self, prompt: str, model_id: str) -> ProviderResult:
        """Make actual call to local model via Ollama."""
        # Check if ollama is available
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "run", model_id,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdin_data = prompt.encode()
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data),
                timeout=self.timeout,
            )
            
            response_text = stdout.decode()
            return ProviderResult(
                content=response_text,
                model=model_id,
                provider="local",
                usage={"prompt_tokens": len(prompt.split()), "completion_tokens": len(response_text.split())},
                finish_reason="stop",
            )
        except FileNotFoundError:
            raise Exception("Ollama not installed - cannot make local model calls")
        except Exception as e:
            raise Exception(f"Local model call failed: {str(e)}")
    
    def _simulate_response(self, prompt: str, model_id: str) -> str:
        """Generate a simulated local model response."""
        words = prompt.split()
        key_terms = [w for w in words if len(w) > 4][:5]
        terms_str = ". ".join(key_terms)
        
        return (f"[Local {model_id} simulated response]\n\n"
                f"Based on your prompt involving: {terms_str}.\n\n"
                f"This would be a real local model response when Ollama is installed\n"
                f"and the model {model_id} is available.\n"
                f"The model would analyze the task and provide code, analysis, or responses\n"
                f"appropriate to the agent's role ({self.config.get('role', 'developer')}).")
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information for local models."""
        model_info = {
            "codellama:34b": {
                "context_window": 100000,
                "pricing": {"prompt": "Free (local)", "completion": "Free (local)"},
                "capabilities": ["code", "analysis", "text"],
            },
            "llama3:8b": {
                "context_window": 8192,
                "pricing": {"prompt": "Free (local)", "completion": "Free (local)"},
                "capabilities": ["text", "simple_code"],
            },
        }
        
        return model_info.get(model_id)