# RAVEN Architecture Document

## 1. Overview

RAVEN is a terminal-based multi-AI development workspace that coordinates 2-5 AI agents to collaborate on a codebase. The architecture follows a clean separation between the terminal UI, orchestration logic, provider adapters, and configuration management.

## 2. Module Responsibilities

### 2.1. Core Layer (`raven/core/`)
- **orchestrator.py**: Coordinates agent workflow, task distribution, and execution flow
- **team_manager.py**: Manages agent team configuration, role assignment, and team size validation
- **workflow_builder.py**: Builds task workflows based on available roles and team composition
- **scheduler.py**: Schedules task execution with dependency resolution and parallel execution support
- **task_manager.py**: Manages task lifecycle: creation, assignment, execution, completion, and cancellation
- **context_manager.py**: Maintains shared context across agents, project state, and historical events
- **event_bus.py**: Pub-sub event system for inter-component communication (task events, agent status changes, errors)

### 2.2. Agents Layer (`raven/agents/`)
- **base_agent.py**: Abstract base class defining the agent interface, capabilities, and lifecycle methods
- **agent_factory.py**: Factory for creating agent instances based on configuration
- **agent_registry.py**: Registry of available agents and their capabilities
- **role_manager.py**: Manages role definitions, validation, and assignment to agents
- **capability_manager.py**: Tracks agent capabilities and matches them to task requirements
- **prompt_builder.py**: Constructs prompts from agent configurations, roles, and project context
- **communication.py**: Structured communication between agents (result exchange, hand-offs)

### 2.3. Providers Layer (`raven/providers/`)
- **base.py**: Common provider interface defining the contract for all AI providers
- **registry.py**: Provider registry for discovering and looking up available providers
- **openai_provider.py**: Adapter for OpenAI API models (GPT-4, GPT-3.5, etc.)
- **gemini_provider.py**: Adapter for Google Gemini models
- **anthropic_provider.py**: Adapter for Anthropic Claude models
- **openai_compatible.py**: Adapter for OpenAI-compatible APIs (e.g., Together, Anthropic Bedrock)
- **local_provider.py**: Adapter for local/offline models (Ollama, etc.)

### 2.4. Integrations Layer (`raven/integrations/`)
- **base.py**: Common integration interface
- **claude_code.py**: Adapter for Claude Code CLI integration (detect install, execute, parse output)
- **codex_cli.py**: Adapter for Codex CLI integration (detect install, execute, parse output)
- **subprocess_manager.py**: Cross-platform subprocess execution with streaming output
- **capability_detector.py**: Detects available CLI tools and their versions

### 2.5. Tools Layer (`raven/tools/`)
- **filesystem.py**: File system operations with safety guards and path validation
- **terminal.py**: Terminal output handling,Rich integration for formatted logging
- **git_tools.py**: Git operations for checkpointing, diffing, and change tracking
- **test_runner.py**: Test execution and result parsing
- **permission_manager.py**: Permission checks for file operations and shell commands

### 2.6. Workspace Layer (`raven/workspace/`)
- **project_detector.py**: Detects project type, configuration, and relevant files
- **file_indexer.py**: Indexes project files for agent context provision
- **workspace_manager.py**: High-level workspace lifecycle management
- **change_tracker.py**: Tracks modifications, supports Git checkpoints and rollbacks
- **git_manager.py**: Git wrapper for checkpoint management, diff generation, and recovery

### 2.7. Storage Layer (`raven/storage/`)
- **database.py**: SQLite database schema and connection management
- **session_repository.py**: Persists and retrieves session metadata
- **task_repository.py**: Persists and retrieves tasks, events, and results
- **event_repository.py**: Event store for audit trail and session resumption

### 2.8. Security Layer (`raven/security/`)
- **secrets_manager.py**: Secure handling of API keys and secrets (environment variables, vault)
- **command_validator.py**: Validates commands before execution, especially dangerous ones
- **path_validator.py**: Validates file paths for security boundaries
- **approval_manager.py**: Approval workflow for dangerous shell commands and destructive operations

### 2.9. Utilities (`raven/utils/`)
- **logging.py**: Structured logging with Rich integration, color-coded output
- **errors.py**: Custom error types and error handling framework
- **config_loader.py**: YAML/JSON configuration loading with Pydantic validation

### 2.10. TUI Layer (`raven/tui/`)
- **app.py**: Main Textual application instance and control flow
- **screens/**: Individual screens (welcome, project_setup, team_size, agent_setup, live_execution, etc.)
- **widgets/**: Reusable UI components (agent_card, activity_log, status_bar, etc.)
- **theme.tcss**: Color scheme (#080A12 background, #168CFF electric blue, #842BFF purple)
- **raven_logo.py**: ASCII/Unicode-compatible startup logo

### 2.11. CLI Layer (`raven/cli.py`)
- Typer-based CLI commands for workspace creation, configuration, and management

### 2.12. Entry Point (`raven/main.py`)
- Application entry point

## 3. Provider Abstraction

### 3.1. Provider Interface (`raven/providers/base.py`)
```python
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate that API credentials are available and valid"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate a response from the AI model"""
    
    @abstractmethod
    def get_model_info(self, model_id: str) -> dict:
        """Get model information and availability"""
```

### 3.2. Provider Registry (`raven/providers/registry.py`)
- Maps provider names to provider classes
- Validates provider availability at startup
- Configures default models per provider

## 4. Agent Lifecycle

1. **Configuration**: User specifies number of agents (2-5), provider, model, role, and instructions for each
2. **Initialization**: Agent factory creates instances with provider adapters injected
3. **Role Assignment**: Role manager assigns roles; roles are not tied to agent indices
4. **Context Loading**: Each agent receives project context via context manager
5. **Execution**: Agent receives tasks via task manager; executes via provider adapter
6. **Result Exchange**: Agent communicates results via communication module / event bus
7. **Completion**: Task manager marks task complete; orchestrator proceeds to next task
8. **Persistence**: Session repository stores state for resumption

## 5. Task Lifecycle

1. **Creation**: Task created with description, dependencies, and assigned role
2. **Queue**: Task enqueued in task manager based on dependencies
3. **Assignment**: When dependencies satisfied, task assigned to available agent with matching role
4. **Execution**: Agent executes task via provider adapter; output streamed to terminal
5. **Result**: Structured result (text, code, errors, metadata) returned via event bus
6. **Completion**: Task marked complete; downstream tasks may be enqueued
7. **Cancellation**: Task can be cancelled; in-progress execution terminated with timeout

## 6. Event Flow

```
Task Created
    ↓
Team Configuration Complete
    ↓
Orchestrator Initializes Agents
    ↓
Context Loaded per Agent
    ↓
Task Queued
    ↓
Agent Assigned (role match + availability)
    ↓
Provider Adapter Calls Model
    ↓
Response Received
    ↓
Result Exchanged (event_bus + communication)
    ↓
Task Marked Complete
    ↓
Next Task Queued OR Session Ended
    ↓
Terminal UI Updated (live_execution screen)
```

Events published via event_bus:
- `agent_ready`
- `task_assigned`
- `agent_started`
- `agent_completed`
- `agent_failed`
- `task_completed`
- `session_paused`
- `session_resumed`
- `session_stopped`
- `error_occurred`

## 7. Security Boundaries

- **Secrets never stored in SQLite**: API keys fetched at runtime from environment or vault
- **Command validation**: All shell commands validated via command_validator before execution
- **Path validation**: All file paths validated via path_validator to prevent path traversal
- **Approval required**: Dangerous operations require approval via approval_manager
- **No hardcoded credentials**: Configuration files contain placeholder references only
- **Workspace isolation**: Agents operate within the detected project directory only

## 8. Data Flow

```
User Input (Typer CLI or Textual TUI)
    ↓
Configuration Validation (Pydantic models)
    ↓
Session Repository (persist config)
    ↓
Provider Registry Initialize
    ↓
Agent Factory Create Agents
    ↓
Context Manager Load Project Context
    ↓
Orchestrator Start Workflow
    ↓
Task Manager Dispatch Tasks
    ↓
Agent Provider Adapter (API/CLI)
    ↓
AI Model Response
    ↓
Event Bus Update Terminal UI
    ↓
Task Manager Next Task
    ↓
Persistence (session_repository, task_repository)
    ↓
Terminal UI Refresh
```

## 9. Initialization Sequence

1. User runs `raven` CLI or Textual app
2. Welcome screen → Project directory detection
3. Project setup (exists/new)
4. Team size selection (2-5)
5. Per-agent configuration: provider, model, role, instructions
6. Provider validation (credentials tested)
7. Role recommendations displayed; user modifies if desired
8. Session persisted to SQLite
9. Live terminal UI starts with agent activity panels
10. Orchestrator begins task distribution and execution

## 10. Error Handling Principles

- Never fabricate progress or pretend a model is working when it is not
- Timeouts handled with configurable limits; failed tasks marked and skipped
- Retries configured per-provider with exponential backoff
- Failures propagated via event_bus to terminal UI
- Graceful degradation: if one agent fails, others continue if possible
- All errors logged structurally with context (agent_id, task_id, provider, model)