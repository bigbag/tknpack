"""pydantic-ai TokenPackModel integration example.

Shows how to wrap a pydantic-ai model with TokenPackModel to encode
tool results as TOON or PLOON before sending to the LLM, reducing token usage.
"""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from tknpack.ai import TokenPackModel
from tknpack.core import Format, PloonOptions, ToonOptions

# Wrap any pydantic-ai model with TokenPackModel
base_model = OpenAIModel("gpt-4o")

# TOON encoding (default)
toon_model = TokenPackModel(base_model)

# PLOON encoding
ploon_model = TokenPackModel(base_model, format=Format.PLOON)

# Use with an Agent — tool results will be encoded automatically
agent = Agent(
    model=toon_model,
    instructions="You are a helpful assistant.",
)

# With custom TOON options (4-space indent, pipe delimiter)
toon_custom = TokenPackModel(
    base_model,
    options=ToonOptions(indent=4, delimiter="|"),
)

# With custom PLOON options (compact format)
ploon_custom = TokenPackModel(
    base_model,
    format=Format.PLOON,
    options=PloonOptions(compact=True),
)

# Works with FallbackModel too
# from pydantic_ai.models.fallback import FallbackModel
# primary = OpenAIModel("gpt-4o")
# fallback = OpenAIModel("gpt-4o-mini")
# model = TokenPackModel(FallbackModel(primary, fallback), format=Format.PLOON)

print("TokenPackModel wraps any pydantic-ai model transparently.")
print("Tool results (dicts/lists) are encoded as TOON or PLOON before hitting the LLM API.")
print("Text prompts, system instructions, and responses pass through unchanged.")
