"""pydantic-ai TokenPackModel wrapper: encodes tool results before sending to LLM."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from collections.abc import Sequence as ABCSequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart
from pydantic_ai.models import ModelRequestParameters, ModelResponse
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings

from tknpack.core.codec import Codec
from tknpack.core.errors import PloonEncodeError, ToonEncodeError
from tknpack.core.types import Format, PloonOptions, ToonOptions

if TYPE_CHECKING:
    from pydantic_ai._run_context import RunContext
    from pydantic_ai.models import KnownModelName, Model


@dataclass(init=False)
class TokenPackModel(WrapperModel):
    """Model wrapper that encodes ToolReturnPart content using TOON or PLOON before forwarding to the wrapped model.

    Usage:
        model = TokenPackModel(base_model)                                   # TOON with defaults
        model = TokenPackModel(base_model, format=Format.PLOON)              # PLOON with defaults
        model = TokenPackModel(base_model, options=ToonOptions(delimiter="|"))  # TOON with custom options
    """

    codec: Codec

    def __init__(
        self,
        wrapped: Model | KnownModelName,
        *,
        format: Format = Format.TOON,
        options: ToonOptions | PloonOptions | None = None,
    ):
        super().__init__(wrapped)
        self.codec = Codec(format=format, options=options)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        transformed = self._transform_messages(messages)
        return await self.wrapped.request(transformed, model_settings, model_request_parameters)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext | None = None,
    ) -> AsyncIterator:
        transformed = self._transform_messages(messages)
        async with self.wrapped.request_stream(
            transformed, model_settings, model_request_parameters, run_context
        ) as stream:
            yield stream

    def _transform_messages(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        result: list[ModelMessage] = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                new_parts: list[Any] = []
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart) and self._is_encodable(part.content):
                        try:
                            encoded = self.codec.encode(cast(dict | list, part.content))
                            new_parts.append(replace(part, content=encoded))
                        except (ToonEncodeError, PloonEncodeError):
                            new_parts.append(part)
                    else:
                        new_parts.append(part)
                result.append(replace(msg, parts=new_parts))
            else:
                result.append(msg)
        return result

    @staticmethod
    def _is_encodable(content: object) -> bool:
        return isinstance(content, (Mapping, ABCSequence)) and not isinstance(content, (str, bytes))


# Backward-compatible aliases
ToonModel = TokenPackModel
