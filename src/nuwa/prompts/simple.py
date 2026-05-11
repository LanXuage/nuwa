import re
import json

from typing import List, Optional, Dict
from .base import SystemPromptBuilder, Goal, Format, Example, PromptLanguage

LANG_TEMPLATES: Dict[str, Dict[str, str]] = {
    "English": {
        "role_prefix": "Act as a senior ",
        "expert_only": "Act as a expert",
        "expertise_connector": ", ",
        "expertise_with": " with expertise in ",
        "tone": "Use a {tone} tone. ",
        "style": "Use a {style} style",
        "style_with_tone": " with a {tone} tone. ",
        "goal_style": " in a {style} style",
        "goal_style_tone": " with a {tone} tone. ",
        "goal_tone": " in a {tone} tone. ",
        "script_header": "Follow this step-by-step process:\n",
        "step_format": "Step {i}: {step} \n",
        "step_end_punctuation": ".",
        "output_json_schema": "Return a valid JSON object matching this JSON Schema: {schema}\n\n",
        "output_string_format": 'Provide a final answer structured exactly as follows: \n"""\n{format}\n"""\n\n',
        "example_header": 'EXAMPLE {i}:\ninput:\n"""\n{input}\n"""\noutput:\n"""\n{output}\n"""\n\n',
        "constraints_header": "Follow these constraints:\n",
        "constraint_line": "- {constraint}\n",
    },
    "中文": {
        "role_prefix": "作为一位资深的",
        "expert_only": "作为一位专注于{expertise}领域的专家",
        "expertise_connector": "、",
        "expertise_with": "专注于{expertise}领域的资深",
        "tone": "请使用{tone}的语气。",
        "style": "请使用{style}的风格",
        "style_with_tone": "和{tone}的语气。",
        "goal_style": "请使用{style}的风格，",
        "goal_style_tone": "和{tone}的语气，",
        "goal_tone": "请使用{tone}的语气，",
        "script_header": "请按以下步骤执行：\n",
        "step_format": "步骤{i}：{step} \n",
        "step_end_punctuation": "。",
        "output_json_schema": "请根据以下JSON Schema返回一个有效的JSON对象：{schema}\n\n",
        "output_string_format": '请根据以下格式提供最终回应: \n"""\n{format}\n"""\n\n',
        "example_header": '例子{i}：\n输入：\n"""\n{input}\n"""\n输出：\n"""\n{output}\n"""\n\n',
        "constraints_header": "请遵循以下约束：\n",
        "constraint_line": "- {constraint}\n",
    },
}


class SimpleSystemPromptBuilder(SystemPromptBuilder):
    def __init__(
        self,
        role: Optional[str] = None,
        expertise: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        tone: Optional[str] = None,
        style: Optional[str] = None,
        goal: Optional[Goal] = None,
        script: Optional[List[str]] = None,
        promptLang: PromptLanguage = "English",
        reasoningLang: PromptLanguage = "English",
        outputLang: PromptLanguage = "English",
        examples: Optional[List[Example]] = None,
        outputFormat: Optional[Format] = None,
        promptCompletion: Optional[str] = None,
    ):
        self.role = role
        self.expertise = expertise or []
        self.constraints = constraints or []
        self.tone = tone
        self.style = style
        self.goal = goal
        self.script = script or []
        self.promptLang = promptLang
        self.reasoningLang = reasoningLang
        self.outputLang = outputLang
        self.examples = examples or []
        self.outputFormat = outputFormat
        self.promptCompletion = promptCompletion or ""

    @staticmethod
    def _is_empty(val) -> bool:
        if val is None:
            return True
        if isinstance(val, (str, list, dict)):
            return len(val) == 0
        return False

    def _get_lang_cfg(self, lang: str) -> Dict[str, str]:
        cfg = LANG_TEMPLATES.get(lang)
        if cfg is None:
            raise ValueError(f"Unsupported language '{lang}'")
        return cfg

    def set_role(self, role: str) -> "SimpleSystemPromptBuilder":
        self.role = role
        return self

    def set_focused_expertise(
        self, expertise: List[str]
    ) -> "SimpleSystemPromptBuilder":
        self.expertise = expertise
        return self

    def set_constraints(self, constraints: List[str]) -> "SimpleSystemPromptBuilder":
        self.constraints = constraints
        return self

    def set_tone(self, tone: str) -> "SimpleSystemPromptBuilder":
        self.tone = tone
        return self

    def set_style(self, style: str) -> "SimpleSystemPromptBuilder":
        self.style = style
        return self

    def set_goal(self, goal: Goal) -> "SimpleSystemPromptBuilder":
        self.goal = goal
        return self

    def set_script(self, script: List[str]) -> "SimpleSystemPromptBuilder":
        self.script = script
        return self

    def set_prompt_lang(self, lang: PromptLanguage) -> "SimpleSystemPromptBuilder":
        self.promptLang = lang
        return self

    def set_reasoning_lang(self, lang: PromptLanguage) -> "SimpleSystemPromptBuilder":
        self.reasoningLang = lang
        return self

    def set_output_lang(self, lang: PromptLanguage) -> "SimpleSystemPromptBuilder":
        self.outputLang = lang
        return self

    def set_few_shot(self, examples: List[Example]) -> "SimpleSystemPromptBuilder":
        self.examples = examples
        return self

    def set_output_format(self, format: Format) -> "SimpleSystemPromptBuilder":
        self.outputFormat = format
        return self

    def set_prompt_completion(self, prompt: str) -> "SimpleSystemPromptBuilder":
        self.promptCompletion = prompt
        return self

    def _section_role_expertise(self, lang: str) -> str:
        cfg = self._get_lang_cfg(lang)
        has_exp = not self._is_empty(self.expertise)
        result = ""

        if self.role is not None:
            if has_exp:
                exp_list = cfg["expertise_connector"].join(self.expertise)
                if lang == "English":
                    result = f"{cfg['role_prefix']}{self.role}{cfg['expertise_with']}{exp_list}"
                else:
                    result = f"{cfg['role_prefix']}{cfg['expertise_with'].format(expertise=exp_list)}{self.role}"
            else:
                result = f"{cfg['role_prefix']}{self.role}"
        elif has_exp:
            exp_list = cfg["expertise_connector"].join(self.expertise)
            result = cfg["expert_only"].format(expertise=exp_list)

        if result:
            result += ". " if lang == "English" else "。"
        return result

    def _section_goal_tone_style(self, lang: str) -> str:
        cfg = self._get_lang_cfg(lang)
        result = ""

        if self.goal is None:
            if not self._is_empty(self.style):
                result += cfg["style"].format(style=self.style)
                if not self._is_empty(self.tone):
                    result += cfg["style_with_tone"].format(tone=self.tone)
                else:
                    result += ". " if lang == "English" else "。"
            elif not self._is_empty(self.tone):
                result += cfg["tone"].format(tone=self.tone)
        else:
            # goal + 风格/语气
            if not self._is_empty(self.style):
                result += cfg["goal_style"].format(style=self.style)
                if not self._is_empty(self.tone):
                    result += cfg["goal_style_tone"].format(tone=self.tone)
                else:
                    result += ""  # 中文已自带"，"，英文需要加空格前缀
            elif not self._is_empty(self.tone):
                result += cfg["goal_tone"].format(tone=self.tone)
            # 追加 goal 内容
            goal_content = self.goal.content.strip()
            if lang == "English":
                result += f"{self.goal} {goal_content}"
            else:
                result += goal_content
            # 句尾标点
            if lang == "English":
                if not goal_content.endswith("."):
                    result += ". "
                else:
                    result += " "
            else:
                if not goal_content.endswith(("。", "！", "？")):
                    result += "。"
        return result

    def _section_reasoning_output_lang(self, lang: str) -> str:
        result = ""
        if (
            not self._is_empty(self.reasoningLang)
            and self.reasoningLang != self.promptLang
        ):
            if lang == "English":
                result += f"Reason step by step in {self.reasoningLang}, and explain why at each step. "
            else:
                result += f"请使用{self.reasoningLang}进行逐步推理和解释。"
        if not self._is_empty(self.outputLang) and self.outputLang != self.promptLang:
            if lang == "English":
                result += f"Final answer in {self.outputLang}. "
            else:
                result += f"请使用{self.outputLang}输出最终回应。"
        return result

    def _section_script(self, lang: str) -> str:
        if self._is_empty(self.script):
            return ""
        cfg = self._get_lang_cfg(lang)
        text = cfg["script_header"]
        for i, step in enumerate(self.script, start=1):
            step = step.strip()
            # 末尾添加标点
            if lang == "English":
                if re.search(r"\w$", step):
                    step += cfg["step_end_punctuation"]
            else:
                if re.search(r"[\u4e00-\u9fff\w]$", step):
                    step += cfg["step_end_punctuation"]
            text += cfg["step_format"].format(i=i, step=step)
        return text + "\n"

    def _section_output_format(self, lang: str) -> str:
        if self.outputFormat is None:
            return ""
        cfg = self._get_lang_cfg(lang)
        if not isinstance(self.outputFormat, str):
            return cfg["output_json_schema"].format(
                schema=json.dumps(self.outputFormat)
            )
        else:
            return cfg["output_string_format"].format(format=self.outputFormat)

    def _section_examples(self, lang: str) -> str:
        if self._is_empty(self.examples):
            return ""
        cfg = self._get_lang_cfg(lang)
        text = ""
        for i, example in enumerate(self.examples, start=1):
            text += cfg["example_header"].format(
                i=i, input=example.input, output=example.output
            )
        return text

    def _section_constraints(self, lang: str) -> str:
        if self._is_empty(self.constraints):
            return ""
        cfg = self._get_lang_cfg(lang)
        text = cfg["constraints_header"]
        for c in self.constraints:
            text += cfg["constraint_line"].format(constraint=c)
        return text + "\n"

    # ---------- 总拼装 ----------
    def build(self) -> str:
        lang = self.promptLang
        if lang not in LANG_TEMPLATES:
            raise ValueError(f"Unsupported prompt language '{lang}'")

        sections = [
            self._section_role_expertise(lang),
            self._section_goal_tone_style(lang),
            self._section_reasoning_output_lang(lang),
            self._section_script(lang),
            self._section_output_format(lang),
            self._section_examples(lang),
            self._section_constraints(lang),
        ]

        prompt = ""
        for sec in sections:
            if sec:
                prompt += sec
        parts = [s for s in sections if s]
        prompt = "\n\n".join(parts)
        prompt = ""
        buffer = ""
        for sec in sections:
            if sec:
                buffer += sec
        if buffer:
            buffer += self.promptCompletion
        return buffer
