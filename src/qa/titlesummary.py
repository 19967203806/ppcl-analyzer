from langchain_core.language_models.chat_models import BaseChatModel

from ..utils.model_factory import invoke_text

class TitleSummarizer:
    """Generate short chat titles through the shared LangChain model."""

    def __init__(self, model: BaseChatModel):
        self.model = model
        self.prompt_template = (
            "Summarize the following chat into a concise title (<=20 chars, no quotes, no punctuation):\n{history}"
        )

    def _invoke(self, text: str) -> str:
        try:
            result = invoke_text(
                self.model,
                system_prompt="You are a concise title summarizer, generating simple titles without quotes or punctuation.",
                user_prompt=self.prompt_template.format(history=text),
            )
            return (result.get("content") or "").strip()
        except Exception:
            return ""

    def summarize(self, history: list[dict]) -> str:
        if not history:
            return "New chat"
        recent = history[-8:]
        text = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
        try:
            title = self._invoke(text)
        except Exception:
            # Use the first user message when title generation is unavailable.
            title = next((m["content"] for m in recent if m["role"] == "user"), "Chat")
        return title[:50] or "Chat"
