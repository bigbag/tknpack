from typing import TypeVar

from pydantic import BaseModel

from tknpack.core import (
    Codec,
    Format,
    PloonOptions,
    ToonOptions,
    ploon_decode,
    ploon_encode,
    ploon_is_valid,
    ploon_minify,
    ploon_prettify,
    toon_decode,
    toon_encode,
)

T = TypeVar("T", bound=BaseModel)

__version__ = "0.1.0"
__all__ = [
    "Codec",
    "encode",
    "decode",
    "toon_encode",
    "toon_decode",
    "ToonOptions",
    "ploon_encode",
    "ploon_decode",
    "ploon_minify",
    "ploon_prettify",
    "ploon_is_valid",
    "PloonOptions",
    "Format",
    "__version__",
]


def encode(
    model: BaseModel,
    options: ToonOptions | PloonOptions | None = None,
    *,
    format: Format = Format.TOON,
) -> str:
    codec = Codec(format=format, options=options)
    return codec.encode(model.model_dump(mode="json"))


def decode(
    text: str,
    model_class: type[T],
    *,
    format: Format = Format.TOON,
) -> T:
    codec = Codec(format=format)
    data = codec.decode(text)
    # Unwrap single-record PLOON results for Pydantic models
    if format == Format.PLOON and isinstance(data, dict) and len(data) == 1:
        val = next(iter(data.values()))
        if isinstance(val, list) and len(val) == 1 and isinstance(val[0], dict):
            data = val[0]
    return model_class.model_validate(data)
