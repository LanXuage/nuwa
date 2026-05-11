import logging

from ..contexts.simple import SimpleContext

from ..llms import LLM

from ..tools import ToolKit

from .base import Task, Agent
from ..contexts import Context
from ..prompts import PromptBuilder
from datetime import timedelta
from typing import Union

logger = logging.getLogger(__name__)


class ReActAgent(Agent):

    def __init__(self, prompt: Union[str, PromptBuilder], llm: LLM) -> None:
        self.prompt = prompt
        self.llm = llm

    async def execute_task(
        self,
        task: Task,
        toolkit: ToolKit | None = None,
        context: Context | None = None,
        timeout: timedelta = timedelta(minutes=10),
        max_steps: int = 10,
        **kwargs,
    ) -> None:
        if self.llm is None:
            raise RuntimeError("ReActAgent requires an LLM callable (set self.llm)")
        if toolkit is None:
            logger.warning("No ToolKit provided; agent will work without tools")

        if context is None:
            context = SimpleContext()
