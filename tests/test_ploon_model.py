"""Tests for the pydantic-ai TokenPackModel wrapper with PLOON format."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolReturnPart,
)
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

from tknpack.ai import TokenPackModel
from tknpack.core import Format, PloonOptions


@dataclass
class RecordingModel(Model):
    last_messages: list[ModelMessage] | None = None

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        self.last_messages = messages
        return ModelResponse(
            parts=[TextPart(content="ok")],
            usage=RequestUsage(),
            model_name="test",
            timestamp=datetime.now(timezone.utc),
        )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context=None,
    ) -> AsyncIterator:
        self.last_messages = messages
        yield ModelResponse(
            parts=[TextPart(content="ok")],
            usage=RequestUsage(),
            model_name="test",
            timestamp=datetime.now(timezone.utc),
        )

    @property
    def model_name(self) -> str:
        return "test"

    @property
    def system(self) -> str:
        return "test"


class TestPloonModelEncoding:
    async def test_dict_content_is_ploon_encoded(self):
        inner = RecordingModel()
        model = TokenPackModel(inner, format=Format.PLOON)
        messages = [ModelRequest(parts=[ToolReturnPart(tool_name="t", content={"items": [{"id": 1, "name": "A"}]})])]
        await model.request(messages, None, ModelRequestParameters())
        assert inner.last_messages is not None
        part = inner.last_messages[0].parts[0]
        assert isinstance(part, ToolReturnPart)
        content = part.content
        assert isinstance(content, str)
        assert "[items#1]" in content
        assert "1:1" in content

    async def test_list_content_is_ploon_encoded(self):
        inner = RecordingModel()
        model = TokenPackModel(inner, format=Format.PLOON)
        messages = [ModelRequest(parts=[ToolReturnPart(tool_name="t", content=[{"x": 1}, {"x": 2}])])]
        await model.request(messages, None, ModelRequestParameters())
        part = inner.last_messages[0].parts[0]
        assert isinstance(part.content, str)
        assert "[#2]" in part.content

    async def test_string_content_unchanged(self):
        inner = RecordingModel()
        model = TokenPackModel(inner, format=Format.PLOON)
        messages = [ModelRequest(parts=[ToolReturnPart(tool_name="t", content="plain text")])]
        await model.request(messages, None, ModelRequestParameters())
        part = inner.last_messages[0].parts[0]
        assert part.content == "plain text"

    async def test_custom_ploon_options(self):
        inner = RecordingModel()
        model = TokenPackModel(inner, format=Format.PLOON, options=PloonOptions(compact=True))
        messages = [ModelRequest(parts=[ToolReturnPart(tool_name="t", content={"items": [{"id": 1}]})])]
        await model.request(messages, None, ModelRequestParameters())
        part = inner.last_messages[0].parts[0]
        content = part.content
        assert isinstance(content, str)
        assert ";" in content
        assert "\n" not in content


class TestToonModelAlias:
    async def test_toon_model_alias_works(self):
        from tknpack.ai import ToonModel

        inner = RecordingModel()
        model = ToonModel(inner)
        messages = [ModelRequest(parts=[ToolReturnPart(tool_name="t", content={"key": "value"})])]
        await model.request(messages, None, ModelRequestParameters())
        part = inner.last_messages[0].parts[0]
        assert isinstance(part.content, str)
        assert "key: value" in part.content
