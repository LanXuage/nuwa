from mcp.types import Tool as MCPTool
from .models import ToolParameter, ToolObjectParameter, ToolEntity


def get_tool_entity(tool: MCPTool) -> ToolEntity:
    properties = {}
    for k, v in tool.inputSchema.get("properties", {}).items():
        if not isinstance(v, dict):
            continue
        t = v.get("type")
        if not isinstance(t, str):
            for to in v.get("anyOf", []):
                if not isinstance(to, dict):
                    continue
                t = to.get("type")
                if isinstance(t, str):
                    if t == "integer":
                        t = "number"
                    break
        if t in ["object", "string", "number", "boolean", "array"]:
            properties[k] = ToolParameter(type=t, description=v.get("description"))  # type: ignore
    parameters = ToolObjectParameter(type="object", properties=properties)
    return ToolEntity(
        name=tool.name, parameters=parameters, description=tool.description
    )
