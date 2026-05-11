from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Dict, Optional, TypeAlias
from pydantic import BaseModel

from ..tools import ToolKit

from ..contexts import Context


class StartInfo(BaseModel):
    timestamp: int


ThinkStartInfo: TypeAlias = StartInfo


class ActionStartInfo(StartInfo):
    name: str


class Timing(BaseModel):
    start_time: int
    end_time: int
    duration: Optional[int] = None


class Cost(BaseModel):
    input_tokens: int
    output_tokens: int
    cost: int
    coin: str


class ResultSchema(Timing, Cost):
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Optional[dict] = None


ThinkResult: TypeAlias = ResultSchema


class AgentResult(ResultSchema):
    step_count: int


class Delta(BaseModel):
    content: str


ThinkDelta: TypeAlias = Delta


class ActionDelta(Delta):
    name: str
    args: Dict[str, Any]
    current_arg_name: Optional[str] = None
    current_arg_Value: Optional[str] = None


class ActionResult(ResultSchema):
    name: str
    args: Dict[str, Any]


class Task(BaseModel):
    content: str


class Agent(ABC):
    @abstractmethod
    async def execute_task(
        self,
        task: Task,
        toolkit: Optional[ToolKit] = None,
        context: Optional[Context] = None,
        timeout: timedelta = timedelta(minutes=10),
        max_steps: int = 10,
        **kwargs,
    ) -> None:
        raise NotImplementedError
