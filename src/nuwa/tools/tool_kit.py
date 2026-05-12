import re
import logging
import asyncio
import typing

from json_repair import loads
from typing import Dict, Optional, Callable, List, Union

from .models import (
    Tool,
    ToolObjectParameter,
    ToolParameter,
    ToolArrayParameter,
    ToolEntity,
    ToolInvocation,
)

Tools = Dict[str, Tool]

ToolResponse = Union[
    str, int, float, Dict[str, "ToolResponse"], List["ToolResponse"], bool
]


logger = logging.getLogger(__name__)


class ToolKit:
    def __init__(self, tools: Tools = {}) -> None:
        self._tools: Tools = tools.copy()

    def tool(
        self,
        name: Optional[str] = None,
        parameters: ToolObjectParameter = ToolObjectParameter(
            type="object", properties={}, required=[]
        ),
        description: Optional[str] = None,
    ):

        def decorator(func: Callable):
            tool_name = name or func.__name__
            desc = description or func.__doc__

            annotations = {}
            if isinstance(func.__annotations__, dict):
                annotations = func.__annotations__
            for k, v in annotations.items():
                if k == "return":
                    continue

                if k in parameters.properties:
                    continue

                item_type = v
                item_desc = None

                if hasattr(v, "__metadata__"):
                    item_type = v.__args__[0] if hasattr(v, "__args__") else v
                    item_desc = (
                        getattr(v, "__metadata__", (None,))[0]
                        if hasattr(v, "__metadata__")
                        else None
                    )
                elif isinstance(v, typing._AnnotatedAlias):  # type: ignore
                    item_type = v.__args__[0]
                    item_desc = (v.__metadata__ or ("",))[0]

                if item_type in [int, float]:
                    parameters.properties[k] = ToolParameter(
                        type="number", description=item_desc
                    )
                elif item_type in [bool]:
                    parameters.properties[k] = ToolParameter(
                        type="boolean", description=item_desc
                    )
                elif item_type in [dict]:
                    parameters.properties[k] = ToolObjectParameter(
                        type="object", description=item_desc
                    )
                elif item_type in [list]:
                    parameters.properties[k] = ToolArrayParameter(
                        type="array",
                        items=ToolParameter(type="string", description=item_desc),
                    )
                else:
                    parameters.properties[k] = ToolParameter(
                        type="string", description=item_desc
                    )

            self.add_tool(
                tool=Tool(
                    func=func,
                    entity=ToolEntity(
                        name=tool_name, parameters=parameters, description=desc
                    ),
                ),
            )
            logger.debug("Registered tool: %s", tool_name)
            return func

        return decorator

    def add_tool(
        self, tool: Tool, tool_name: Optional[str] = None, overwrite: bool = False
    ):
        if tool_name is None:
            tool_name = tool.entity.name
        if overwrite or not self.has_tool(tool_name=tool_name):
            self._tools[tool_name] = tool

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        return self._tools.get(tool_name)

    def get_tools(self, pattern: str) -> List[Tool]:
        pattern_compiled = re.compile(pattern)
        return [v for k, v in self._tools.items() if pattern_compiled.match(k)]

    def __getitem__(self, key: str) -> List[Tool]:
        return self.get_tools(key)

    def __setitem__(self, key: str, value: Tool):
        return self.add_tool(tool=value, tool_name=key, overwrite=True)

    def keys(self):
        return self._tools.keys()

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def clear_tools(self):
        self._tools.clear()

    async def call_tool(self, func: ToolInvocation) -> ToolResponse:
        logger.debug("call tool %s", func)
        tool = self.get_tool(func.get("name"))
        if not tool:
            raise ValueError(f"Tool '{func.get('name')}' not found")

        args = loads(func.get("arguments"))
        if isinstance(args, dict):
            result = tool.func(**args)
        elif isinstance(args, list):
            result = tool.func(*args)
        else:
            result = tool.func(args)

        if asyncio.iscoroutine(result):
            return await result
        else:
            return result
