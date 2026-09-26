from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage

from src.utils import model_factory


def test_create_qwen_model_uses_openai_compatible_settings(monkeypatch):
    constructor = Mock(return_value=Mock())
    monkeypatch.setattr(model_factory, "ChatOpenAI", constructor)

    model_factory.create_chat_model(
        {
            "MODEL_PROVIDER": "qwen",
            "MODEL_NAME": "qwen-plus",
            "OPENAI_API_KEY": "secret",
            "OPENAI_BASE_URL": "https://example.test/v1",
            "MODEL_REQUEST_TIMEOUT": "12",
            "MODEL_MAX_RETRIES": "2",
        }
    )

    constructor.assert_called_once_with(
        model="qwen-plus",
        api_key="secret",
        base_url="https://example.test/v1",
        timeout=12.0,
        max_retries=2,
        stream_usage=True,
    )


def test_create_azure_model_uses_client_credential_provider(monkeypatch):
    constructor = Mock(return_value=Mock())
    monkeypatch.setattr(model_factory, "AzureChatOpenAI", constructor)
    config = {
        "MODEL_PROVIDER": "azure",
        "AZURE_OPENAI_ENDPOINT": "https://azure.test",
        "AZURE_OPENAI_DEPLOYMENT": "deployment",
        "AZURE_OPENAI_API_VERSION": "2024-10-21",
        "AZURE_CLIENT_ID": "client",
        "AZURE_CLIENT_SECRET": "secret",
        "AZURE_TENANT_ID": "tenant",
    }

    model_factory.create_chat_model(config)

    kwargs = constructor.call_args.kwargs
    assert kwargs["azure_endpoint"] == "https://azure.test"
    assert kwargs["azure_deployment"] == "deployment"
    assert isinstance(
        kwargs["azure_ad_token_provider"],
        model_factory.ClientCredentialTokenProvider,
    )
    assert kwargs["stream_usage"] is True


def test_create_model_reports_all_missing_configuration():
    with pytest.raises(RuntimeError) as exc:
        model_factory.create_chat_model({"MODEL_PROVIDER": "qwen"})
    assert "MODEL_NAME" in str(exc.value)
    assert "OPENAI_API_KEY" in str(exc.value)


def test_client_credential_provider_caches_token(monkeypatch):
    response = Mock()
    response.json.return_value = {"access_token": "token"}
    post = Mock(return_value=response)
    monkeypatch.setattr(model_factory.requests, "post", post)
    provider = model_factory.ClientCredentialTokenProvider(
        "tenant", "client", "secret"
    )

    assert provider() == "token"
    assert provider() == "token"
    assert post.call_count == 1


def test_message_usage_normalizes_langchain_metadata():
    message = AIMessage(
        content="ok",
        usage_metadata={
            "input_tokens": 2,
            "output_tokens": 3,
            "total_tokens": 5,
        },
    )
    assert model_factory.message_usage(message) == {
        "prompt_tokens": 2,
        "completion_tokens": 3,
        "total_tokens": 5,
    }
