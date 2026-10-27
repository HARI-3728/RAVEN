# RAVEN - Requirements Document

## 1. Functional Requirements

### A. Dynamic Team Configuration
- The user chooses 2, 3, 4, or 5 agents at workspace creation
- Generate exactly that number of agent configurations
- Every agent has a configurable provider, model, role, and instructions
- Roles are not fixed to specific agent numbers
- Allow predefined and custom roles
- Allow one agent to perform multiple responsibilities
- Recommend suitable roles based on team size and the user's project
- Let the user modify recommendations before execution

### B. AI Provider Integration
- Build a common provider interface
- Support real API-based model integrations through provider-specific adapters
- Support configurable model identifiers
- Validate credentials and model availability
- Never hardcode API keys
- Keep secrets out of source control and logs
- Do not claim an integration works until tested

### C. Terminal-based AI Tools
- Design a separate adapter layer for Claude Code and Codex CLI
- Detect whether supported CLIs are installed
- Use official supported execution and output interfaces
- Do not assume CLI output exposes every internal tool call
- Never confuse an API integration with a CLI integration
- Do not implement fake CLI support

### D. Collaboration
- Build an orchestrator, task manager, workflow builder, scheduler, and shared context manager
- Support task dependencies and appropriate parallel execution
- Let agents exchange structured results
- Adapt workflows to the available roles and the task
- Prevent uncontrolled concurrent edits to the same files
- Handle timeouts, failures, cancellation, and retries

### E. Live Terminal
- Display the active project and configured agents
- Display each agent's provider, model, role, and real execution status
- Show actual requests, responses, observable tool activity, task events, and errors
- Provide a shared activity feed and agent-specific inspection
- Allow the user to enter instructions during execution
- Provide pause, resume, stop, task inspection, and change-review controls
- Never fabricate progress or pretend a model is working when it is not

### F. Project Workspace
- Detect the selected project directory
- Read relevant project files
- Give agents appropriate project context
- Track modifications and support Git checkpoints
- Review diffs before applying sensitive changes
- Require appropriate approval for dangerous shell commands and destructive operations

### G. Persistence
- Store session metadata, tasks, events, and team configurations
- Allow previous sessions to be resumed
- Never store API secrets in ordinary SQLite records or project configuration files

## 2. Non-Functional Requirements

- Terminal-first application, NOT a web application
- Do not add React, Next.js, Vite, a browser-based dashboard, or FastAPI unless a documented future requirement genuinely needs them
- Black background: #080A12
- Electric blue: #168CFF
- Purple: #842BFF
- Modern, premium, cyber-inspired terminal aesthetic
- Readable monospace typography
- Clear agent status indicators, activity panels, and keyboard shortcuts
- Use Typed models for agents, tasks, events, and results
- Use structured logging
- Design for Windows compatibility
- Keep configuration local to each project where appropriate
- Avoid unnecessary frameworks and premature abstractions

## 3. Constraints

- Python 3.11+ only
- Must use: Textual, Rich, Typer, Pydantic, Asyncio, SQLite, Pytest, Git
- Team size: 2-5 agents
- No hardcoded API keys
- No secrets in source control or logs
- ASCII/Unicode-compatible startup logo only (no graphical assets required)
- Keep terminal UI separate from orchestration logic
- Keep provider adapters independent of agent roles
- Keep roles independent of agent indices

## 4. Acceptance Criteria

- [ ] Project folder structure matches the specified layout
- [ ] pyproject.toml configured with dependencies, entry points, and pytest settings
- [ ] .env.example contains placeholder variable names only
- [ ] docs/requirements.md contains all functional and non-functional requirements
- [ ] docs/architecture.md describes module responsibilities, provider abstraction, agent lifecycle, task lifecycle, event flow, security boundaries, and data flow
- [ ] docs/development-roadmap.md defines all five implementation stages
- [ ] docs/provider-integration.md documents provider integration approach
- [ ] docs/security.md documents security boundaries and secrets management
- [ ] Starter YAML configuration files present (default.yaml, providers.yaml, roles.yaml, team_templates.yaml)
- [ ] Initial tests pass (configuration parsing, team-size constraints, basic project initialization)
- [ ] Project can be installed in a Python virtual environment
- [ ] README with Windows PowerShell setup and launch instructions created