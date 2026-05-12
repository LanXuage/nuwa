from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TypeAlias, Literal, Union

from openai import BaseModel
from ..contexts import Context

PromptLanguage: TypeAlias = Literal["English", "中文"]


class Example(BaseModel):
    input: str
    output: str

class Goal(ABC):
    action: str
    content: str


class JSONSchema(BaseModel):
    type: Optional[str] = None
    properties: Optional[Dict[str, "JSONSchema"]] = None
    items: Optional[Union["JSONSchema", List["JSONSchema"]]] = None
    required: Optional[List[str]] = None

    class Config:
        extra = "allow"


Format: TypeAlias = Union[str, JSONSchema]


class PromptBuilder(ABC):
    @abstractmethod
    def build(self, context: Optional[Context] = None) -> str:
        raise NotImplementedError


class SystemPromptBuilder(PromptBuilder):

    @abstractmethod
    def set_role(self, role: str) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_focused_expertise(
        self, expertise: List[str]
    ) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_constraints(self, constraints: List[str]) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_tone(self, tone: str) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_style(self, style: str) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_goal(self, goal: Goal) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_script(self, script: List[str]) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_prompt_lang(self, lang: PromptLanguage) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_reasoning_lang(self, lang: PromptLanguage) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_output_lang(self, lang: PromptLanguage) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_few_shot(self, examples: List[Example]) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_output_format(self, format: Format) -> "SystemPromptBuilder":
        raise NotImplementedError

    @abstractmethod
    def set_prompt_completion(self, prompt: str) -> "SystemPromptBuilder":
        raise NotImplementedError
