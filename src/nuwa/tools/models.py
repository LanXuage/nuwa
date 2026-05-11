from pydantic import BaseModel
from typing import Union, Literal, Optional, Dict, List, Callable, TypedDict


class ToolInvocation(TypedDict):
    name: str
    arguments: str


class ToolParameter(BaseModel):

    type: Literal["object", "string", "number", "boolean", "array"]
    description: Optional[str] = None
    enum: Optional[List[str]] = None


class ToolArrayParameter(ToolParameter):

    items: Union["ToolObjectParameter", "ToolArrayParameter", ToolParameter]


class ToolObjectParameter(ToolParameter):

    properties: Dict[
        str, Union["ToolObjectParameter", ToolArrayParameter, ToolParameter]
    ] = {}
    required: List[str] = []


class ToolEntity(BaseModel):

    name: str
    parameters: Union[ToolObjectParameter, ToolParameter] = ToolObjectParameter(
        type="object", properties={}, required=[]
    )
    description: Optional[str] = None


class Tool:

    def __init__(self, func: Callable, entity: ToolEntity):

        self.func = func
        self.entity = entity
