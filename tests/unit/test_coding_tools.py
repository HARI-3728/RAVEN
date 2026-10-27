"""Unit tests for CodingTools workspace capabilities."""

import os
import tempfile
import pytest
from raven.tools.coding_tools import CodingTools, ToolExecutionResult


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some initial files
        test_file = os.path.join(tmpdir, "sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        sub_dir = os.path.join(tmpdir, "subdir")
        os.makedirs(sub_dir)
        with open(os.path.join(sub_dir, "nested.txt"), "w", encoding="utf-8") as f:
            f.write("hello from nested file\n")

        yield tmpdir


@pytest.mark.asyncio
async def test_list_dir(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_list_dir()
    assert res.success
    assert "sample.py" in res.output
    assert "subdir" in res.output


@pytest.mark.asyncio
async def test_read_file(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_read_file(path="sample.py")
    assert res.success
    assert "def add(a, b):" in res.output
    assert "return a + b" in res.output


@pytest.mark.asyncio
async def test_write_file(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_write_file(path="new_dir/test.txt", content="created by test")
    assert res.success
    assert "Successfully wrote" in res.output

    # Verify file actually created
    created_path = os.path.join(temp_workspace, "new_dir", "test.txt")
    assert os.path.exists(created_path)
    with open(created_path, "r", encoding="utf-8") as f:
        assert f.read() == "created by test"


@pytest.mark.asyncio
async def test_edit_file(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_edit_file(
        path="sample.py",
        target_text="return a + b",
        replacement_text="return a + b  # sum",
    )
    assert res.success
    assert "Successfully edited" in res.output or "Successfully updated" in res.output

    # Verify file content
    with open(os.path.join(temp_workspace, "sample.py"), "r", encoding="utf-8") as f:
        content = f.read()
    assert "return a + b  # sum" in content


@pytest.mark.asyncio
async def test_edit_file_target_not_found(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_edit_file(
        path="sample.py",
        target_text="def nonexistent():",
        replacement_text="pass",
    )
    assert not res.success
    assert "Target text not found" in res.error


@pytest.mark.asyncio
async def test_grep_search(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_grep_search(query="nested file")
    assert res.success
    assert "nested.txt" in res.output


@pytest.mark.asyncio
async def test_run_command_safe(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_run_command(command="python -c \"print('raven_ok')\"")
    assert res.success
    assert "raven_ok" in res.output


@pytest.mark.asyncio
async def test_path_traversal_blocked(temp_workspace):
    tools = CodingTools(project_root=temp_workspace)
    res = await tools.tool_read_file(path="../../outside.txt")
    assert not res.success
    assert "escapes project boundary" in res.error.lower() or "traversal" in res.error.lower()


@pytest.mark.asyncio
async def test_approval_rejection_blocks_execution(temp_workspace):
    # Callback always rejects
    def deny_all(action, details):
        return False

    tools = CodingTools(project_root=temp_workspace, approval_callback=deny_all)
    res = await tools.tool_write_file(path="forbidden.txt", content="should not be written")
    assert not res.success
    assert "cancelled by user" in res.error.lower() or "not approved" in res.error.lower()
    assert not os.path.exists(os.path.join(temp_workspace, "forbidden.txt"))
