from .base import (
    AssistantTurn,
    Message,
    ModelInterface,
    ModelSpec,
    MockModel,
    ToolCall,
)
from .anthropic import AnthropicModel
from .openai_compat import OpenAICompatModel

PROVIDERS = {
    "anthropic": AnthropicModel,
    "openai-compat": OpenAICompatModel,
    "mock": MockModel,
}


def build_model(spec: ModelSpec) -> ModelInterface:
    """Instantiate the adapter named by spec.provider. This is the ONLY place
    provider classes are resolved; swapping the brain is a config edit."""
    try:
        cls = PROVIDERS[spec.provider]
    except KeyError:
        raise ValueError(
            f"Unknown provider {spec.provider!r}. Known: {sorted(PROVIDERS)}"
        ) from None
    return cls(spec)


__all__ = [
    "AssistantTurn",
    "Message",
    "ModelInterface",
    "ModelSpec",
    "MockModel",
    "ToolCall",
    "AnthropicModel",
    "OpenAICompatModel",
    "build_model",
    "PROVIDERS",
]
