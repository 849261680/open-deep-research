from __future__ import annotations

from backend.app.research.agent import ResearchAgent
from backend.app.research.config import ResearchConfig
from backend.app.research.tools import CodeExecutionTool
from backend.app.research.tools import ToolSecurityError


def test_code_execution_tool_schema_is_explicit() -> None:
    schema = CodeExecutionTool.schema()

    assert schema["name"] == "python_code_execution"
    assert "Python" in schema["description"]
    assert schema["parameters"]["required"] == ["code"]
    assert schema["parameters"]["properties"]["code"]["type"] == "string"
    assert schema["parameters"]["additionalProperties"] is False


def test_code_execution_tool_runs_normal_python() -> None:
    result = CodeExecutionTool().run("print(sum([1, 2, 3]))")

    assert result.stdout.strip() == "6"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.timed_out is False


def test_code_execution_tool_blocks_unsafe_os_system() -> None:
    tool = CodeExecutionTool()

    try:
        tool.run("import os\nos.system('echo unsafe')")
    except ToolSecurityError as exc:
        assert "Blocked unsafe import: os" in str(exc)
    else:
        raise AssertionError("unsafe code should be blocked")


def test_code_execution_tool_reports_timeout() -> None:
    result = CodeExecutionTool().run("while True:\n    pass\n", timeout_seconds=1)

    assert result.timed_out is True
    assert result.exit_code is None
    assert "timed out" in result.error


def test_research_config_registers_tool_schema() -> None:
    config = ResearchConfig()

    assert config.tool_schemas()[0]["name"] == "python_code_execution"


def test_research_agent_can_execute_registered_tool() -> None:
    agent = ResearchAgent(query="calculate")

    result = agent.execute_tool(
        "python_code_execution",
        {"code": "print(21 * 2)", "timeout_seconds": 1},
    )

    assert result.stdout.strip() == "42"
