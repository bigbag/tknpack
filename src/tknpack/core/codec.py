"""Unified codec: single interface for both TOON and PLOON encoding/decoding."""

from __future__ import annotations

from dataclasses import dataclass

from tknpack.core.ploon import ploon_decode, ploon_encode
from tknpack.core.toon import toon_decode, toon_encode
from tknpack.core.types import Format, PloonOptions, ToonOptions


@dataclass
class Codec:
    """Unified encoder/decoder supporting TOON and PLOON formats.

    Usage:
        codec = Codec(Format.PLOON)
        encoded = codec.encode(data)
        decoded = codec.decode(encoded)
    """

    format: Format = Format.TOON
    options: ToonOptions | PloonOptions | None = None

    def encode(self, data: dict | list | str | int | float | bool | None) -> str:
        if self.format == Format.PLOON:
            return ploon_encode(data, self.options if isinstance(self.options, PloonOptions) else None)
        return toon_encode(data, self.options if isinstance(self.options, ToonOptions) else None)

    def decode(self, text: str) -> dict | list | str | int | float | bool | None:
        if self.format == Format.PLOON:
            return ploon_decode(text, self.options if isinstance(self.options, PloonOptions) else None)
        return toon_decode(text)
