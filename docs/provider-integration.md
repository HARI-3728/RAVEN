# RAVEN Provider Integration Document

## 1. Overview

RAVEN supports AI model integration through a provider abstraction layer. Each provider implements a common interface, enabling the orchestrator to interact with different AI models through a unified API. Providers are swapped via configuration; no code changes are required.

## 2. Provider Interface

### 2.1. Core Contract (`raven/providers/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json

class ProviderResult:
    """Structured result from a provider call."""
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None

class AIProvider(ABC):
    """Common interface for all AI model providers."""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__.lower()
    
    @abstractmethod
    async def generate_response(self, 
                                prompt: str, 
                                context: str = "",
                                model: Optional[str] = None) -> ProviderResult:
        """Generate a response from the AI model.
        
        Args:
            prompt: The user prompt/request
            context: Additional project context
            model: Optional model override from configuration
            
        Returns:
            ProviderResult with response content and metadata
        """
        pass
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate that API credentials are available and valid.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        pass
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information and availability.
        
        Args:
            model_id: The model identifier to look up
            
        Returns:
            Dictionary with model info or None if not found
        """
        return None
    
    def get_supported_models(self) -> list:
        """Get list of supported model identifiers for this provider.
        
        Returns:
            List of model IDs supported by this provider
        """
        return []
    
    def format_prompt(self, system: str, user: str) -> str:
        """Format a system/user prompt pair for this provider.
        
        Different providers have different prompt formatting requirements.
        This method handles the formatting convention for each provider.
        
        Args:
            system: System prompt/instructions
            user: User message/content
            
        Returns:
            Formatted prompt string ready for API call
        """
        return f"System: {system}\nUser: {user}"
```

### 2.2. Provider Result Structure

All provider responses conform to `ProviderResult`:
- `content`: The model's text response
- `model`: The model identifier that was used
- `provider`: The provider name
- `usage`: Token usage information (if available)
- `finish_reason`: Why the model stopped generating
- `raw_response`: The raw API response for debugging

## 3. Provider Registry

### 3.1. Registry Function (`raven/providers/registry.py`)

The provider registry:
- Maps provider names to provider classes
- Validates provider availability at startup
- Configures default models per provider
- Handles provider-specific configuration

```python
from typing import Dict, Type
from .base import AIProvider

class ProviderRegistry:
    """Registry of available AI providers."""
    
    def __init__(self):
        self._providers: Dict[str, Type[AIProvider]] = {}
        self._default_models: Dict[str, str] = {}
    
    def register(self, name: str, provider_class: Type[AIProvider]) -> None:
        """Register a provider class under a name."""
        self._providers[name] = provider_class
    
    def get(self, name: str) -> Type[AIProvider]:
        """Get a provider class by name."""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
        return self._providers[name]
    
    def list_providers(self) -> list:
        """List all registered provider names."""
        return list(self._providers.keys())
    
    def set_default_model(self, provider_name: str, model_id: str) -> None:
        """Set the default model for a provider."""
        self._default_models[provider_name] = model_id
    
    def get_default_model(self, provider_name: str) -> Optional[str]:
        """Get the default model for a provider."""
        return self._default_models.get(provider_name)
    
    def create_instance(self, provider_name: str, config: dict) -> AIProvider:
        """Create a provider instance from configuration."""
        provider_class = self.get(provider_name)
        return provider_class(config)
```

### 3.2. Built-in Providers

#### 3.2.1. OpenAI Provider (`raven/providers/openai_provider.py`)
- Integrates with OpenAI API (GPT-4, GPT-3.5-turbo, etc.)
- Uses `OPENAI_API_KEY` environment variable
- Implements `generate_response` via `openai.AsyncCompletions` or `ChatCompletions`
- Implements `validate_credentials` by testing API key
- Model info includes context window, pricing, capabilities

#### 3.2.2. Gemini Provider (`raven/providers/gemini_provider.py`)
- Integrates with Google Gemini API
- Uses `GEMINI_API_KEY` environment variable
- Implements same interface as other providers

#### 3.2.3. Anthropic Provider (`raven/providers/anthropic_provider.py`)
- Integrates with Anthropic Claude API
- Uses `ANTHROPIC_API_KEY` environment variable
- Implements same interface

#### 3.2.4. OpenAI-Compatible Provider (`raven/providers/openai_compatible.py`)
- Integrates with any OpenAI-compatible API (Together, Bedrock, etc.)
- Configurable API base URL and API key
- Uses `OPENAI_COMPATIBLE_API_KEY` and `OPENAI_COMPATIBLE_BASE_URL` env vars

#### 3.2.5. Local Provider (`raven/providers/local_provider.py`)
- Integrates with local/offline models via Ollama or similar
- Uses local subprocess calls to model inference engine
- No API key required
- Model identifiers correspond to locally installed Ollama models

## 4. Configuration Schema

### 4.1. Provider Configuration (YAML: `configs/providers.yaml`)

```yaml
providers:
  openai:
    api_key_env: OPENAI_API_KEY
    default_model: gpt-4o
    supported_models:
      - gpt-4o
      - gpt-4-turbo
      - gpt-3.5-turbo
    timeout: 30
    max_retries: 2
    
  gemini:
    api_key_env: GEMINI_API_KEY
    default_model: gemini-1.5-flash
    supported_models:
      - gemini-1.5-flash
      - gemini-1.5-pro
    timeout: 30
    max_retries: 2
    
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    default_model: claude-3-opus-20240229
    supported_models:
      - claude-3-opus-20240229
      - claude-3-sonnet-20240229
      - claude-3-haiku-20240307
    timeout: 30
    max_retries: 2
    
  local:
    api_key_env: ""  # Not required
    default_model: codellama:34b
    supported_models:
      - codellama:34b
      - llama3:8b
    timeout: 60
    max_retries: 3
```

### 4.2. Agent Configuration (YAML: `configs/team_templates.yaml`)

```yaml
team_templates:
  developer_team:
    count: 3
    agents:
      - provider: openai
        model: gpt-4o
        role: developer
        instructions: "Write clean, maintainable code following best practices"
      
      - provider: anthropic
        model: claude-3-sonnet-20240229
        role: reviewer
        instructions: "Review code for quality, security, and best practices"
      
      - provider: openai
        model: gpt-4o
        role: tester
        instructions: "Write and run tests for the code changes"

  data_analysis_team:
    count: 4
    agents:
      - provider: openai
        model: gpt-4o
        role: analyst
        instructions: "Analyze data and provide insights"
      
      - provider: anthropic
        model: claude-3-opus-20240229
        role: interpreter
        instructions: "Interpret data and explain findings"
      
      - provider: gemini
        model: gemini-1.5-pro
        role: visualizer
        instructions: "Create visual representations of data trends"
      
      - provider: local
        model: codellama:34b
        role: iterator
        instructions: "Iterate over data structures and extract values"
```

## 5. Credential Management

### 5.1. Never Hardcode API Keys

- API keys are never stored in source code, configuration files committed to version control, or logs
- All credentials sourced from environment variables at runtime
- `.env.example` provides placeholder variable names only
- Production deployments use secret management (environment, vault, etc.)

### 5.2. Environment Variable Mapping

| Provider | Environment Variable |
|----------|---------------------|
| OpenAI | `OPENAI_API_KEY` |
| Gemini | `GEMINI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI-Compatible | `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL` |
| Local | None required |

### 5.3. Credential Validation

```python
# Example validation flow
def validate_provider_credentials(provider_name: str, config: dict) -> bool:
    """Validate credentials for a provider before adding agent."""
    provider_class = PROVIDER_REGISTRY.get(provider_name)
    if not provider_class:
        return False
    
    instance = provider_class(config)
    return instance.validate_credentials()
```

### 5.4. Model Availability Validation

```python
def validate_model_availability(provider_name: str, model_id: str) -> bool:
    """Validate that a model is available with the given credentials."""
    provider_class = PROVIDER_REGISTRY.get(provider_name)
    if not provider_class:
        return False
    
    instance = provider_class({})
    model_info = instance.get_model_info(model_id)
    return model_info is not None
```

## 6. Integration Workflow

### 6.1. Adding a New Provider

1. Create a new file in `raven/providers/` following the `AIProvider` interface
2. Implement `generate_response`, `validate_credentials`, and optionally `get_model_info`
3. Register the provider in `raven/providers/registry.py`
4. Add configuration to `configs/providers.yaml`
5. Add environment variable documentation to `.env.example`
6. Test credential validation and model availability
7. Add unit tests for the provider implementation

### 6.2. Provider Initialization in Application

```python
# From team configuration
provider_config = {
    "name": "openai",
    "api_key_env": "OPENAI_API_KEY",
    "default_model": "gpt-4o",
    "supported_models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "timeout": 30,
    "max_retries": 2,
}

provider = PROVIDER_REGISTRY.create_instance("openai", provider_config)

# Validate before use
if not provider.validate_credentials():
    print("Warning: OpenAI credentials invalid or missing")

# Check model availability
if not provider.get_model_info("gpt-4o"):
    print("Warning: gpt-4o model not available with current credentials")
```

## 7. Testing Provider Integrations

Each provider implementation includes:

- **Unit tests**: `tests/unit/providers/test_<provider>.py`
  - Test credential validation (valid/invalid keys)
  - Test model info lookup
  - Test prompt formatting
  - Test error handling

- **Integration tests**: `tests/integration/providers/`
  - Test actual API calls (if API keys available)
  - Test model response generation
  - Test rate limiting and retries

> **Important**: Do not claim an integration works until tested. Provider adapters are stubbed/mocked by default; real API integrations require valid credentials and are validated during testing.

## 8. Provider Independence from Agent Roles

- Provider selection is independent of agent role assignment
- Any agent can use any provider (configured per-agent)
- Role selection is independent of agent index (Agent 1 could use Anthropic, Agent 2 could use OpenAI)
- Provider adapters have no knowledge of agent roles or workflow position