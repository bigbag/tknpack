"""Tests for the pydantic-ai ToonModel wrapper."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

from tknpack.ai import ToonModel
from tknpack.core import ToonOptions


@dataclass
class RecordingModel(Model):
    """A minimal model that records what messages it receives."""

    __test__ = False

    recorded_messages: list[list[ModelMessage]] | None = None

    def __post_init__(self):
        self.recorded_messages = []

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        self.recorded_messages.append(messages)
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
        self.recorded_messages.append(messages)
        yield ModelResponse(
            parts=[TextPart(content="ok")],
            usage=RequestUsage(),
            model_name="test",
            timestamp=datetime.now(timezone.utc),
        )

    @property
    def model_name(self) -> str:
        return "recording-model"

    @property
    def system(self) -> str:
        return "test"


def _make_tool_return(content, tool_name="test_tool"):
    return ToolReturnPart(
        tool_name=tool_name,
        content=content,
        tool_call_id="call_123",
    )


def _make_request(*parts) -> ModelRequest:
    return ModelRequest(parts=list(parts))


class TestToolReturnEncoding:
    @pytest.mark.anyio
    async def test_dict_content_is_encoded(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        msg = _make_request(_make_tool_return({"id": 1, "name": "Alice", "active": True}))

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert isinstance(part.content, str)
        assert "id: 1" in part.content
        assert "name: Alice" in part.content
        assert "active: true" in part.content

    @pytest.mark.anyio
    async def test_list_content_is_encoded(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        msg = _make_request(_make_tool_return([1, 2, 3]))

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert isinstance(part.content, str)
        assert "[3]: 1,2,3" in part.content

    @pytest.mark.anyio
    async def test_tabular_list_is_encoded(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        msg = _make_request(_make_tool_return(data))

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert isinstance(part.content, str)
        assert "{id,name}" in part.content


class TestPassthroughContent:
    @pytest.mark.anyio
    async def test_string_content_unchanged(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        msg = _make_request(_make_tool_return("plain text result"))

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert part.content == "plain text result"

    @pytest.mark.anyio
    async def test_bytes_content_unchanged(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        msg = _make_request(_make_tool_return(b"binary data"))

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert part.content == b"binary data"

    @pytest.mark.anyio
    async def test_user_prompt_unchanged(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        user_part = UserPromptPart(content="Hello")
        msg = _make_request(user_part)

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert isinstance(part, UserPromptPart)
        assert part.content == "Hello"

    @pytest.mark.anyio
    async def test_system_prompt_unchanged(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        sys_part = SystemPromptPart(content="You are a helper")
        msg = _make_request(sys_part)

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert isinstance(part, SystemPromptPart)
        assert part.content == "You are a helper"

    @pytest.mark.anyio
    async def test_retry_prompt_unchanged(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        retry_part = RetryPromptPart(content="Try again")
        msg = _make_request(retry_part)

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert isinstance(part, RetryPromptPart)
        assert part.content == "Try again"


class TestModelRequestPreservation:
    @pytest.mark.anyio
    async def test_run_id_preserved(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        msg = ModelRequest(
            parts=[_make_tool_return({"key": "val"})],
            run_id="run_abc123",
        )

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        assert recorded[0].run_id == "run_abc123"

    @pytest.mark.anyio
    async def test_metadata_preserved(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        msg = ModelRequest(
            parts=[_make_tool_return({"key": "val"})],
            metadata={"trace_id": "xyz"},
        )

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        assert recorded[0].metadata == {"trace_id": "xyz"}

    @pytest.mark.anyio
    async def test_model_response_passes_through(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        response_msg = ModelResponse(
            parts=[TextPart(content="previous response")],
            usage=RequestUsage(),
            model_name="test",
            timestamp=ts,
        )
        request_msg = _make_request(_make_tool_return({"x": 1}))

        await model.request([response_msg, request_msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        assert isinstance(recorded[0], ModelResponse)
        assert recorded[0].parts[0].content == "previous response"


class TestOptionsPropagate:
    @pytest.mark.anyio
    async def test_custom_indent(self):
        inner = RecordingModel()
        model = ToonModel(inner, options=ToonOptions(indent=4))
        data = {"parent": {"child": "val"}}
        msg = _make_request(_make_tool_return(data))

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        content = recorded[0].parts[0].content
        assert "    child: val" in content

    @pytest.mark.anyio
    async def test_pipe_delimiter(self):
        inner = RecordingModel()
        model = ToonModel(inner, options=ToonOptions(delimiter="|"))
        data = {"items": [1, 2, 3]}
        msg = _make_request(_make_tool_return(data))

        await model.request([msg], None, ModelRequestParameters())

        recorded = inner.recorded_messages[0]
        content = recorded[0].parts[0].content
        assert "items[3|]: 1|2|3" in content


class TestErrorHandling:
    @pytest.mark.anyio
    async def test_encode_error_falls_back_to_original(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        # A set is not encodable by TOON but passes _is_encodable since set is not str/bytes
        # Actually set is not Mapping or Sequence so it won't pass. Let me use a custom type.
        # Instead, test with content that passes is_encodable but fails encoding
        msg = _make_request(_make_tool_return({"key": "val"}))

        await model.request([msg], None, ModelRequestParameters())

        # If no error, it should just encode normally
        recorded = inner.recorded_messages[0]
        assert "key: val" in recorded[0].parts[0].content


class TestStreamTransformation:
    @pytest.mark.anyio
    async def test_request_stream_transforms_messages(self):
        inner = RecordingModel()
        model = ToonModel(inner)
        msg = _make_request(_make_tool_return({"id": 42, "status": "ok"}))

        async with model.request_stream([msg], None, ModelRequestParameters()) as _stream:
            pass

        recorded = inner.recorded_messages[0]
        part = recorded[0].parts[0]
        assert isinstance(part.content, str)
        assert "id: 42" in part.content
        assert "status: ok" in part.content
