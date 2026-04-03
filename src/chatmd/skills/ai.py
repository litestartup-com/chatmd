"""AI Skills — /ask, /translate, and AI writing commands."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.providers.base import AIProvider

logger = logging.getLogger(__name__)


class ChatSkill(Skill):
    """AI chat / ask skill — sends user text to AI and returns the response."""

    name = "ask"
    description = "ask"
    category = "ai"
    requires_network = True
    is_async = True
    aliases = ["chat"]

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider

    def set_provider(self, provider: AIProvider) -> None:
        """Inject the AI provider after construction."""
        self._provider = provider

    def execute(
        self, input_text: str, args: dict, context: SkillContext
    ) -> SkillResult:
        if not self._provider:
            return SkillResult(success=False, output="", error=t("error.provider_not_configured"))
        if not input_text.strip():
            return SkillResult(
                success=False, output="", error=t("error.ask_empty_input")
            )

        messages = [{"role": "user", "content": input_text}]

        # Build system prompt to enforce response language
        lang_name = t("ai.language_name")
        system_prompt = t("ai.system_prompt", language=lang_name)

        try:
            response = self._provider.chat(
                messages, skill_name="ask", system_prompt=system_prompt,
            )
            return SkillResult(success=True, output=response)
        except RuntimeError as exc:
            return SkillResult(success=False, output="", error=str(exc))


class TranslateSkill(Skill):
    """AI translation skill — translates text to a target language."""

    name = "translate"
    description = "translate"
    category = "ai"
    requires_network = True
    is_async = True
    aliases = ["tran", "t"]

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider

    def set_provider(self, provider: AIProvider) -> None:
        """Inject the AI provider after construction."""
        self._provider = provider

    def execute(
        self, input_text: str, args: dict, context: SkillContext
    ) -> SkillResult:
        if not self._provider:
            return SkillResult(success=False, output="", error=t("error.provider_not_configured"))
        if not input_text.strip():
            return SkillResult(
                success=False, output="",
                error=t("error.translate_empty_input"),
            )

        target_lang = args.get("_positional", args.get("lang", t("translate.default_target")))

        prompt = t(
            "translate.prompt",
            target_lang=target_lang,
            input_text=input_text,
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            response = self._provider.chat(messages, skill_name="translate")
            return SkillResult(success=True, output=response)
        except RuntimeError as exc:
            return SkillResult(success=False, output="", error=str(exc))


# ── Prompt-driven AI writing skills ──────────────────────────────────────


class _PromptAISkill(Skill):
    """Base class for prompt-driven AI writing skills.

    Subclasses only need to define class attributes and a ``prompt_key``.
    The prompt is fetched from i18n with ``{input_text}`` interpolation.
    """

    category = "ai"
    requires_network = True
    is_async = True
    prompt_key: str = ""       # i18n key for the prompt template
    empty_error_key: str = ""  # i18n key for empty-input error

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider

    def set_provider(self, provider: AIProvider) -> None:
        """Inject the AI provider after construction."""
        self._provider = provider

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        if not self._provider:
            return SkillResult(
                success=False, output="",
                error=t("error.provider_not_configured"),
            )
        if not input_text.strip():
            return SkillResult(
                success=False, output="",
                error=t(self.empty_error_key),
            )

        prompt = t(self.prompt_key, input_text=input_text)
        messages = [{"role": "user", "content": prompt}]

        try:
            response = self._provider.chat(messages, skill_name=self.name)
            return SkillResult(success=True, output=response)
        except RuntimeError as exc:
            return SkillResult(success=False, output="", error=str(exc))


class RewriteSkill(_PromptAISkill):
    """AI rewrite / rephrase text."""

    name = "rewrite"
    description = "rewrite"
    aliases = ["rw"]
    prompt_key = "rewrite.prompt"
    empty_error_key = "error.rewrite_empty_input"


class ExpandSkill(_PromptAISkill):
    """AI expand / elaborate text."""

    name = "expand"
    description = "expand"
    aliases = ["exp"]
    prompt_key = "expand.prompt"
    empty_error_key = "error.expand_empty_input"


class PolishSkill(_PromptAISkill):
    """AI grammar check and polish text."""

    name = "polish"
    description = "polish"
    aliases = ["pol"]
    prompt_key = "polish.prompt"
    empty_error_key = "error.polish_empty_input"


class SummarySkill(_PromptAISkill):
    """AI summarize text."""

    name = "summary"
    description = "summary"
    aliases = ["sum"]
    prompt_key = "summary.prompt"
    empty_error_key = "error.summary_empty_input"


class TagSkill(_PromptAISkill):
    """AI extract keywords / tags."""

    name = "tag"
    description = "tag"
    aliases: list[str] = []
    prompt_key = "tag.prompt"
    empty_error_key = "error.tag_empty_input"


class TitleSkill(_PromptAISkill):
    """AI recommend title."""

    name = "title"
    description = "title"
    aliases: list[str] = []
    prompt_key = "title.prompt"
    empty_error_key = "error.title_empty_input"


# ── Skill type for return annotation ─────────────────────────────────────
_WritingSkills = list[_PromptAISkill]


def register_ai_skills(
    router: object,
    provider: AIProvider | None = None,
) -> tuple[ChatSkill, TranslateSkill]:
    """Register all AI skills and return core ones for provider injection."""
    chat_skill = ChatSkill(provider)
    translate_skill = TranslateSkill(provider)
    router.register(chat_skill)  # type: ignore[attr-defined]
    router.register(translate_skill)  # type: ignore[attr-defined]

    # Writing skills
    writing_classes: list[type[_PromptAISkill]] = [
        RewriteSkill, ExpandSkill, PolishSkill,
        SummarySkill, TagSkill, TitleSkill,
    ]
    for cls in writing_classes:
        skill = cls(provider)
        router.register(skill)  # type: ignore[attr-defined]

    return chat_skill, translate_skill
