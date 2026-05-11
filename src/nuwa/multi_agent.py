import json
import logging
from uuid import uuid4
from datetime import timedelta
from typing import List, Optional

from pydantic import TypeAdapter

from .agents.base import Agent, Task
from .tools.models import ToolEntity
from .tools import ToolKit
from .contexts import Context

logger = logging.getLogger(__name__)


class MultiRoleAgent(Agent):
    """Multi-role agent that selects among roles, extends the Agent ABC."""

    def __init__(
        self,
        role_name: str,
        role_prompt: str,
        roles: Optional[List[str]] = None,
        excluded_roles: Optional[List[str]] = None,
        session_id: str = "",
        **kwargs,
    ) -> None:
        self.role_name = role_name
        self.role_prompt = role_prompt
        self.roles = roles or []
        self.excluded_roles = excluded_roles or []
        if role_name not in self.excluded_roles:
            self.excluded_roles.append(role_name)
        self.session_id = session_id or str(uuid4())

    def _format_tools(self, toolkit: ToolKit) -> str:
        """Serialize toolkit entities to JSON string for prompt injection."""
        entities = []
        for name in toolkit.list_tools():
            tool = toolkit.get_tool(name)
            if tool is not None:
                entities.append(tool.entity)
        adapter: TypeAdapter = TypeAdapter(List[ToolEntity])
        return adapter.dump_json(entities, indent=None, exclude_none=True).decode()

    def _format_tool_schema(self, toolkit: ToolKit) -> str:
        """Generate the tool call JSON schema for the prompt."""
        return json.dumps(
            obj={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": toolkit.list_tools(),
                        "description": "调用的工具名称",
                    },
                    "action_input": {
                        "type": ["string", "object"],
                        "description": "调用的工具参数，参考对应工具的JSON Schema描述",
                    },
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def build_system_prompt(
        self, instruction: str, toolkit: Optional[ToolKit] = None
    ) -> str:
        """Build the system prompt from instruction and toolkit info."""
        tools_json = "[]"
        schema_json = "{}"
        if toolkit:
            tools_json = self._format_tools(toolkit)
            schema_json = self._format_tool_schema(toolkit)

        return """你是一个ReAct Agent，请尽可能有效且准确地回应用户的需求。

以下是用户对你的思考（T）和动作（A）的核心要求：{instruction}。

你拥有使用以下工具的权限：{tools}。

请遵循以下流程顺序和格式：
<Q>用户输入的问题</Q><T>结合之前的步骤和后续可能的操作步骤来分析</T><A>调用工具须提供的JSON对象（JSON Schema：{tool_call_json_schema}）</A><O>结合之前的步骤对<action>的结果进行关键数据提取或总结，以便于后续步骤参考或引用</O>... (重复T->A->O步骤，直到可以回复用户问题)<A>{{"action": "answer","action_input": "给用户的最终回应"}}</A>""".format(
            instruction=json.dumps(
                obj={"instruction": instruction},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            tools=tools_json,
            tool_call_json_schema=schema_json,
        )

    async def execute_task(
        self,
        task: Task,
        toolkit: Optional[ToolKit] = None,
        context: Optional[Context] = None,
        timeout: timedelta = timedelta(minutes=10),
        max_steps: int = 10,
        **kwargs,
    ) -> None:
        logger.info(
            "MultiRoleAgent [%s] received task: %s", self.role_name, task.content
        )
        # TODO: implement multi-role ReAct loop with role selection
        raise NotImplementedError("MultiRoleAgent.execute_task is not yet implemented")
