# RAVEN Development Roadmap

## Overview
RAVEN will be implemented in 5 stages, each delivering incremental value while maintaining a working terminal application. The stages are designed to be shippable independently, with each building upon the previous one.

## Stage 1: Foundation and Configuration (Current Step)
**Goal**: Establish the complete project foundation, folder structure, configuration, and basic validation.

**Deliverables**:
- Full folder structure matching the specification
- pyproject.toml with dependencies, entry points, and pytest settings
- .env.example with placeholder variable names only
- Starter YAML configuration files (default.yaml, providers.yaml, roles.yaml, team_templates.yaml) with documented schemas
- docs/requirements.md with functional and non-functional requirements
- docs/architecture.md describing module responsibilities, provider abstraction, agent lifecycle, task lifecycle, event flow, security boundaries, and data flow
- docs/development-roadmap.md defining all five implementation stages
- docs/provider-integration.md and docs/security.md
- README with Windows PowerShell setup and launch instructions
- Initial tests validating configuration parsing, team-size constraints, and basic project initialization
- Project installable in a Python virtual environment

**Key Foundations**:
- Python 3.11+ package with Pydantic configuration models
- Textual for terminal UI framework
- Rich for terminal rendering and logging
- Typer for CLI commands
- SQLite for session and task persistence
- Event bus architecture for inter-component communication

**Blockers to Resolve**:
- None (foundation-first approach)

---

## Stage 2: Agent Configuration and Provider Abstraction
**Goal**: Enable dynamic team configuration, provider integration framework, and basic agent initialization.

**Deliverables**:
- Dynamic team configuration: user chooses 2, 3, 4, or 5 agents at workspace creation
- Common provider interface (`raven/providers/base.py`) with contract definition
- Provider registry for discovering and looking up available providers
- Provider-specific adapters: openai_provider.py, gemini_provider.py, anthropic_provider.py (mock/test implementations)
- Agent base class (`raven/agents/base_agent.py`) with lifecycle methods
- Agent factory for creating agent instances from configuration
- Role manager for role definitions and assignment (roles not tied to agent indices)
- Team size validation (2-5 agents)
- Project directory detection and context loading
- Basic Textual TUI: welcome screen, project setup, team size selection
- Configuration persistence to SQLite
- Tests for team-size constraints and configuration parsing

**Key Foundations**:
- Provider abstraction layer enabling swap between API providers
- Pydantic models for agent, provider, and role configuration
- SQLite schema for sessions, agents, tasks
- Textual app navigation flow

**Blockers to Resolve**:
- Provider adapter implementation details (API key handling, request formatting)
- Cross-platform CLI detection for later stages

---

## Stage 3: Core Orchestration and Collaboration
**Goal**: Build the orchestrator, task manager, workflow builder, scheduler, and shared context manager with task dependencies and parallel execution.

**Deliverables**:
- Orchestrator coordinating agent workflow and execution flow
- Task manager with full lifecycle: creation, assignment, execution, completion, cancellation
- Workflow builder creating task workflows based on available roles and task requirements
- Scheduler with dependency resolution and appropriate parallel execution
- Shared context manager maintaining project state across agents
- Event bus fully operational for inter-component communication
- Task dependencies support (some tasks must complete before others start)
- Controlled parallel execution (prevent uncontrolled concurrent edits to same files)
- Timeout, failure, cancellation, and retry handling
- Agent communication: structured result exchange between agents
- Pause, resume, stop controls for execution
- Live terminal UI updates: agent activity panels, status bar, activity log

**Key Foundations**:
- Asyncio-based orchestration for concurrent agent operation
- Structured task and event models
- Dependency graph for task scheduling
- Controlled concurrency primitives

**Blockers to Resolve**:
- Precise timeout and retry strategy design
- Deadlock prevention in task dependencies
- Realistic parallel execution limits for terminal environment

---

## Stage 4: AI Tool Integrations and Live Execution
**Goal**: Implement Claude Code and Codex CLI adapters, live terminal execution, and real agent activity display.

**Deliverables**:
- Claude Code adapter (`raven/integrations/claude_code.py`) with CLI detection and execution
- Codex CLI adapter (`raven/integrations/codex_cli.py`) with CLI detection and execution
- Subprocess manager for cross-platform process execution with streaming output
- Capability detector: identifies available CLIs and their versions
- Base integration interface (`raven/integrations/base.py`)
- Live execution screen in Textual: real-time agent activity display
- Request/response display in terminal
- Observable tool activity display
- Task events and error display in terminal
- Agent-specific inspection screen
- Shared activity feed
- Allow user to enter instructions during execution
- Pause, resume, stop controls operational in live UI
- Never fabricate progress: real status only

**Key Foundations**:
- Real CLI integration (not fake/simulated)
- Streaming subprocess output to terminal
- CLI installation detection and version checking
- Output parsing and sanitization

**Blockers to Resolve**:
- Cross-platform CLI installation paths and detection
- CLI output parsing reliability
- Real-time output without blocking orchestration

---

## Stage 5: Advanced Features and Polish
**Goal**: Complete the feature set with Git integration, approval workflows, advanced collaboration, and production readiness.

**Deliverables**:
- Git integration: checkpoint support, diff review, change tracking
- Approval workflow for dangerous shell commands and destructive operations
- File diff review before applying sensitive changes
- Prevent uncontrolled concurrent edits to same files
- Comprehensive test suite (unit + integration)
- Multiple predefined roles with recommendations based on team size and project type
- Custom role creation and modification
- One agent performing multiple responsibilities support
- Session resumption from previous saved state
- Full README with setup and launch instructions for all platforms
- Performance optimization for multi-agent coordination
- Error recovery and graceful degradation
- Production packaging and distribution

**Key Foundations**:
- Git tools for checkpoint and diff management
- Command and path validation security
- Session persistence and restoration
- Mature error handling and recovery

**Blockers to Resolve**:
- None (all features designed in earlier stages)

---

## Stage Progression Principles

1. **Each stage delivers a working, testable application** - no empty shells
2. **Later stages build on earlier foundations** - no redundant work
3. **UI is functional at every stage** - Textual app always has a working interface
4. **Configuration is validated early** - Pydantic models catch errors before execution
5. **Security and persistence from Stage 1** - secrets never hardcoded, SQLite from start