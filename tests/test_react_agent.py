"""Tests for the new ReActAgent class using the post-refactor API."""

from unittest.mock import AsyncMock, Mock
from datetime import timedelta

import pytest

from src.nuwa.agents.base import Agent, Task
from src.nuwa.agents.react_agent import ReActAgent
from src.nuwa.contexts.simple import SimpleContext
from src.nuwa.llms.base import LLM
from src.nuwa.tools import ToolKit
from src.nuwa.tools.models import ToolParameter, ToolEntity, Tool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm() -> Mock:
    """A mock LLM that returns a minimal ChatCompletion."""
    llm = Mock(spec=LLM)
    llm.chat = AsyncMock()
    llm.chat_stream = Mock()
    return llm


@pytest.fixture
def toolkit_with_tool() -> ToolKit:
    """A ToolKit pre-registered with one simple tool."""
    tk = ToolKit()

    def echo(text: str) -> str:
        return text

    tk.add_tool(
        Tool(
            func=echo,
            entity=ToolEntity(
                name="echo",
                description="Echo back the input",
                parameters=ToolParameter(type="string", description="The text to echo"),
            ),
        )
    )
    return tk


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestReActAgentInit:
    """Verify basic construction and ABC compliance."""

    def test_init_with_string_prompt(self, mock_llm: Mock) -> None:
        agent = ReActAgent(prompt="You are helpful.", llm=mock_llm)
        assert agent.prompt == "You are helpful."
        assert agent.llm is mock_llm

    def test_implements_agent_abc(self, mock_llm: Mock) -> None:
        agent = ReActAgent(prompt="test", llm=mock_llm)
        assert isinstance(agent, Agent)

    def test_execute_task_raises_when_llm_is_none(self) -> None:
        agent = ReActAgent(prompt="test", llm=None)  # type: ignore[arg-type]
        task = Task(content="Hello")
        with pytest.raises(RuntimeError, match="requires an LLM"):
            # We need to run the async method
            import asyncio

            asyncio.run(agent.execute_task(task))


# ---------------------------------------------------------------------------
# execute_task basic flows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_task_returns_none(mock_llm: Mock) -> None:
    """execute_task is currently a stub — it should return None quietly."""
    agent = ReActAgent(prompt="You are helpful.", llm=mock_llm)
    task = Task(content="What is 2+2?")
    result = await agent.execute_task(task)
    assert result is None


@pytest.mark.asyncio
async def test_execute_task_creates_default_context(mock_llm: Mock) -> None:
    """When no context is provided, a SimpleContext should be used."""
    agent = ReActAgent(prompt="You are helpful.", llm=mock_llm)
    task = Task(content="Hello")
    # The stub sets context = SimpleContext() when context is None.
    # We can't inspect the local variable, but the call should not raise.
    await agent.execute_task(task)


@pytest.mark.asyncio
async def test_execute_task_with_explicit_context(mock_llm: Mock) -> None:
    """A user-supplied context should be accepted."""
    agent = ReActAgent(prompt="You are helpful.", llm=mock_llm)
    task = Task(content="Hello")
    ctx = SimpleContext()
    await agent.execute_task(task, context=ctx)


@pytest.mark.asyncio
async def test_execute_task_with_toolkit(
    mock_llm: Mock, toolkit_with_tool: ToolKit
) -> None:
    """Passing a toolkit should not raise."""
    agent = ReActAgent(prompt="You are helpful.", llm=mock_llm)
    task = Task(content="Echo 'hello'")
    await agent.execute_task(task, toolkit=toolkit_with_tool)


@pytest.mark.asyncio
async def test_execute_task_with_timeout(mock_llm: Mock) -> None:
    """Custom timeout should be accepted."""
    agent = ReActAgent(prompt="You are helpful.", llm=mock_llm)
    task = Task(content="Hello")
    await agent.execute_task(task, timeout=timedelta(seconds=5))


@pytest.mark.asyncio
async def test_execute_task_with_max_steps(mock_llm: Mock) -> None:
    """Custom max_steps should be accepted."""
    agent = ReActAgent(prompt="You are helpful.", llm=mock_llm)
    task = Task(content="Hello")
    await agent.execute_task(task, max_steps=3)
