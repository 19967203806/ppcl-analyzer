import os
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any

import requests
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI, ChatOpenAI

load_dotenv()


ZERO_USAGE = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
}
_default_model: BaseChatModel | None = None
_model_lock = threading.Lock()


class ClientCredentialTokenProvider:
    """Callable Entra token provider with a small in-process cache."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        *,
        refresh_after: float = 3600,
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_after = refresh_after
        self._token: str | None = None
        self._token_time = 0.0
        self._lock = threading.Lock()

    def __call__(self) -> str:
        now = time.monotonic()
        if self._token and now - self._token_time < self.refresh_after:
            return self._token

        with self._lock:
            now = time.monotonic()
            if self._token and now - self._token_time < self.refresh_after:
                return self._token
            try:
                response = requests.post(
                    f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "https://cognitiveservices.azure.com/.default",
                        "grant_type": "client_credentials",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                token = response.json().get("access_token")
                if not token:
                    raise RuntimeError(
                        "Azure token response did not include an access token"
                    )
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to obtain Azure access token: {exc}"
                ) from exc

            self._token = token
            self._token_time = now
            return token


def _required(config: Mapping[str, str], names: Sequence[str]) -> dict[str, str]:
    missing = [name for name in names if not config.get(name)]
    if missing:
        raise RuntimeError("Missing model configuration: " + ", ".join(missing))
    return {name: config[name] for name in names}


def _build_chat_model(values: Mapping[str, str]) -> BaseChatModel:
    provider = values.get("MODEL_PROVIDER", "azure").lower()
    timeout = float(values.get("MODEL_REQUEST_TIMEOUT", "600"))
    max_retries = int(values.get("MODEL_MAX_RETRIES", "0"))

    if provider == "azure":
        required = _required(
            values,
            (
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_DEPLOYMENT",
                "AZURE_OPENAI_API_VERSION",
                "AZURE_CLIENT_ID",
                "AZURE_CLIENT_SECRET",
                "AZURE_TENANT_ID",
            ),
        )
        token_provider = ClientCredentialTokenProvider(
            tenant_id=required["AZURE_TENANT_ID"],
            client_id=required["AZURE_CLIENT_ID"],
            client_secret=required["AZURE_CLIENT_SECRET"],
        )
        return AzureChatOpenAI(
            azure_endpoint=required["AZURE_OPENAI_ENDPOINT"],
            azure_deployment=required["AZURE_OPENAI_DEPLOYMENT"],
            api_version=required["AZURE_OPENAI_API_VERSION"],
            azure_ad_token_provider=token_provider,
            timeout=timeout,
            max_retries=max_retries,
            stream_usage=True,
        )

    required = _required(values, ("MODEL_NAME", "OPENAI_API_KEY"))
    return ChatOpenAI(
        model=required["MODEL_NAME"],
        api_key=required["OPENAI_API_KEY"],
        base_url=values.get(
            "OPENAI_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        timeout=timeout,
        max_retries=max_retries,
        stream_usage=True,
    )


def create_chat_model(
    config: Mapping[str, str] | None = None,
) -> BaseChatModel:
    """Build a model for explicit config or reuse the process-wide default."""

    if config is not None:
        return _build_chat_model(config)

    global _default_model
    if _default_model is not None:
        return _default_model
    with _model_lock:
        if _default_model is None:
            _default_model = _build_chat_model(os.environ)
        return _default_model


def message_text(message: BaseMessage) -> str:
    """Return plain text for both string and content-block message formats."""

    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "".join(parts)


def message_usage(message: BaseMessage) -> dict[str, int]:
    usage = getattr(message, "usage_metadata", None) or {}
    if usage:
        return {
            "prompt_tokens": int(usage.get("input_tokens", 0) or 0),
            "completion_tokens": int(usage.get("output_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }

    response_metadata: dict[str, Any] = getattr(message, "response_metadata", {}) or {}
    token_usage = response_metadata.get("token_usage") or {}
    return {
        "prompt_tokens": int(token_usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(token_usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(token_usage.get("total_tokens", 0) or 0),
    }


def invoke_text(
    model: BaseChatModel,
    *,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    response = model.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return {
        "content": message_text(response),
        "usage": message_usage(response),
    }
