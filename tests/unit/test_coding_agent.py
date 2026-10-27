"""Unit tests for the CodingAgent execution loop."""

import os
import tempfile
import pytest
from typing import List, Dict, Any, Optional

from raven.providers.base import AIProvider, ProviderResult
from raven.agents.coding_agent import CodingAgent, AgentTaskReport


class MockScriptedProvider(AIProvider):
    """Mock provider that returns pre-scripted responses in sequence."""

    def __init__(self, responses: List[str]):
        super().__init__({})
        self.responses = list(responses)
        self.call_count = 0
        self.received_messages = []

    @property
    def default_model(self) -> str:
        return "mock-model"

    @property
    def supported_models(self) -> List[str]:
        return ["mock-model"]

    async def _get_api_key(self) -> str:
        return "mock-key"

    def _validate_key_format(self, key: str) -> bool:
        return True

    def _model_info_for_model(self, model: str):
        from raven.providers.base import ModelInfo
        return ModelInfo(name=model, max_tokens=4096, capabilities=["tool_use"])

    async def _generate_response_core(self, prompt: str, context: str, model_id: str) -> ProviderResult:
        self.call_count += 1
        resp_text = self.responses.pop(0) if self.responses else "Task completed."
        return ProviderResult(
            content=resp_text,
            model=model_id,
            provider="mock",
        )

    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        model_id: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ProviderResult:
        if messages:
            self.received_messages.append(messages)
        return await self._generate_response_core(prompt, context or "", model_id or self.default_model)


@pytest.fixture
def agent_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.asyncio
async def test_agent_full_loop_executes_tool_and_completes(agent_workspace):
    # Step 1: Model issues a write_file tool call
    step_1_response = """
    I will create math_utils.py with a multiply function.
    <tool_call>
    <name>write_file</name>
    <arguments>
    {"path": "math_utils.py", "content": "def multiply(a, b):\\n    return a * b\\n"}
    </arguments>
    </tool_call>
    """
    # Step 2: After seeing tool result, model issues final response
    step_2_response = "I have successfully created math_utils.py with the requested multiply function."

    mock_prov = MockScriptedProvider([step_1_response, step_2_response])
    agent = CodingAgent(
        provider=mock_prov,
        project_root=agent_workspace,
        model="mock-model",
        max_iterations=5,
    )

    report: AgentTaskReport = await agent.execute_task("Create math_utils.py with multiply function")

    assert report.success
    assert mock_prov.call_count == 2
    assert len(report.tools_executed) == 1
    assert report.tools_executed[0]["name"] == "write_file"
    assert "math_utils.py" in report.files_changed

    # Verify actual file on disk
    file_path = os.path.join(agent_workspace, "math_utils.py")
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        assert "def multiply(a, b):" in f.read()


@pytest.mark.asyncio
async def test_agent_iteration_limit_prevents_infinite_loop(agent_workspace):
    # Model endlessly loops requesting tool calls
    infinite_tool_response = """
    <tool_call>
    <name>list_dir</name>
    <arguments>
    {}
    </arguments>
    </tool_call>
    """
    mock_prov = MockScriptedProvider([infinite_tool_response] * 10)
    agent = CodingAgent(
        provider=mock_prov,
        project_root=agent_workspace,
        model="mock-model",
        max_iterations=3,
    )

    report = await agent.execute_task("Loop test")
    assert not report.success
    assert "Iteration limit reached" in report.error
    assert mock_prov.call_count == 3
