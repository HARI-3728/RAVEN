"""Unit tests for universal tool call parser."""

import pytest
from raven.tools.tool_parser import (
    ToolCall,
    parse_tool_calls_from_text,
    format_tool_definitions_for_prompt,
    format_tool_results_for_prompt,
)


def test_parse_xml_tool_call():
    text = """
    I will inspect the file to see the structure.
    <tool_call>
    <name>read_file</name>
    <arguments>
    {"path": "src/raven/main.py", "start_line": 1, "end_line": 50}
    </arguments>
    </tool_call>
    Let's check the contents.
    """
    calls = parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].arguments["path"] == "src/raven/main.py"
    assert calls[0].arguments["start_line"] == 1
    assert calls[0].arguments["end_line"] == 50


def test_parse_multiple_xml_tool_calls():
    text = """
    <tool_call>
    <name>list_dir</name>
    <arguments>
    {"path": "src"}
    </arguments>
    </tool_call>
    And also:
    <tool_call>
    <name>git_status</name>
    <arguments>
    {}
    </arguments>
    </tool_call>
    """
    calls = parse_tool_calls_from_text(text)
    assert len(calls) == 2
    assert calls[0].name == "list_dir"
    assert calls[0].arguments["path"] == "src"
    assert calls[1].name == "git_status"


def test_parse_markdown_json_tool_call():
    text = """
    ```json
    {
        "tool": "write_file",
        "arguments": {
            "path": "hello.py",
            "content": "print('hello')"
        }
    }
    ```
    """
    calls = parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0].name == "write_file"
    assert calls[0].arguments["path"] == "hello.py"
    assert calls[0].arguments["content"] == "print('hello')"


def test_parse_raw_json_tool_call():
    text = '{"tool": "run_command", "arguments": {"command": "pytest -q"}}'
    calls = parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0].name == "run_command"
    assert calls[0].arguments["command"] == "pytest -q"


def test_no_tool_calls_in_regular_text():
    text = "The authentication system uses JWT tokens stored in the Authorization header."
    calls = parse_tool_calls_from_text(text)
    assert len(calls) == 0


def test_format_tool_definitions():
    defs = [
        {
            "name": "read_file",
            "description": "Read file contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file"},
                },
                "required": ["path"],
            },
        }
    ]
    formatted = format_tool_definitions_for_prompt(defs)
    assert "Tool: read_file" in formatted
    assert "Read file contents" in formatted
    assert "<tool_call>" in formatted


def test_format_tool_results():
    results = [
        {"name": "read_file", "output": "print('hello')\n", "success": True, "error": None}
    ]
    formatted = format_tool_results_for_prompt(results)
    assert "<tool_result name=\"read_file\" status=\"success\">" in formatted
    assert "print('hello')" in formatted
