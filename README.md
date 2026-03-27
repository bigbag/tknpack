# tknpack

[![CI](https://github.com/bigbag/tknpack/workflows/CI/badge.svg)](https://github.com/bigbag/tknpack/actions?query=workflow%3ACI)
[![pypi](https://img.shields.io/pypi/v/tknpack.svg)](https://pypi.python.org/pypi/tknpack)
[![downloads](https://img.shields.io/pypi/dm/tknpack.svg)](https://pypistats.org/packages/tknpack)
[![versions](https://img.shields.io/pypi/pyversions/tknpack.svg)](https://github.com/bigbag/tknpack)
[![license](https://img.shields.io/github/license/bigbag/tknpack.svg)](https://github.com/bigbag/tknpack/blob/master/LICENSE)

Token-optimized serialization for Pydantic models using TOON and PLOON formats. Reduce LLM token usage by up to 60% compared to JSON while maintaining full round-trip fidelity.

## Features

- **Dual format support** - TOON (indentation-based) and PLOON (path-based) serialization
- **Pydantic v2 integration** - `encode()` / `decode()` for any `BaseModel`
- **pydantic-ai wrapper** - `TokenPackModel` transparently encodes tool results before sending to LLMs
- **Unified Codec** - Single `Codec` class for both formats with configurable options
- **Round-trip safe** - Encode and decode without data loss
- **Zero extra dependencies** - Core requires only `pydantic>=2.0`

## Quick Start

```python
from tknpack import encode, decode, Format
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
    active: bool

user = User(name="Ada", age=30, active=True)

# TOON encoding (default)
toon = encode(user)
print(toon)
# name: Ada
# age: 30
# active: true

# PLOON encoding
ploon = encode(user, format=Format.PLOON)
print(ploon)
# [root#1](name,age,active)
#
# 1:1|Ada|30|true

# Decode back to Pydantic model
restored = decode(toon, User)
assert restored == user
```

## Installation

```bash
# Install with pip
pip install tknpack

# Or install with uv
uv add tknpack

# With pydantic-ai support (optional)
pip install 'tknpack[ai]'
# or
uv add 'tknpack[ai]'
```

The `ai` extra installs `pydantic-ai>=1.0`, required for the `TokenPackModel` wrapper.

## Usage

### Codec API

The `Codec` class provides a unified interface for both formats:

```python
from tknpack.core import Codec, Format, ToonOptions, PloonOptions

# TOON with defaults
codec = Codec()
encoded = codec.encode({"id": 1, "name": "Ada"})
decoded = codec.decode(encoded)

# PLOON with defaults
codec = Codec(Format.PLOON)
encoded = codec.encode({"users": [{"id": 1, "name": "Ada"}]})

# Custom options
codec = Codec(Format.TOON, ToonOptions(indent=4, delimiter="|"))
codec = Codec(Format.PLOON, PloonOptions(compact=True))
```

### Pydantic Models

```python
from tknpack import encode, decode, Format

# TOON (default)
toon_str = encode(model)
restored = decode(toon_str, MyModel)

# PLOON
ploon_str = encode(model, format=Format.PLOON)
restored = decode(ploon_str, MyModel, format=Format.PLOON)
```

### pydantic-ai Integration

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from tknpack.ai import TokenPackModel
from tknpack.core import Format, PloonOptions

# TOON encoding (default)
model = TokenPackModel(OpenAIModel("gpt-4o"))

# PLOON encoding with compact format
model = TokenPackModel(
    OpenAIModel("gpt-4o"),
    format=Format.PLOON,
    options=PloonOptions(compact=True),
)

agent = Agent(model=model)
# Tool results are automatically encoded before hitting the LLM API
```

## Format Comparison

### TOON ([Text Object Oriented Notation](https://github.com/ulpi-io/toon-spec))

Indentation-based, human-readable format:

```
name: tknpack
tasks[3,]{id,title,completed}:
  1,Implement encoder,true
  2,Write tests,true
  3,Add docs,false
```

### PLOON ([Path-Level Object Oriented Notation](https://www.ploon.ai))

Path-based format with single schema declaration for maximum token efficiency:

```
[tasks#3](id,title,completed)

1:1|1|Implement encoder|true
1:2|2|Write tests|true
1:3|3|Add docs|false
```

### Token Savings

- **TOON** - ~50% reduction vs JSON
- **PLOON** - ~60% reduction vs JSON

## Configuration Options

### ToonOptions

- `indent` (int, default `2`) - Indentation spaces
- `delimiter` (str, default `,`) - Field delimiter character

### PloonOptions

- `field_delimiter` (str, default `|`) - Separator between values
- `path_separator` (str, default `:`) - Separator in array paths (depth:index)
- `compact` (bool, default `False`) - Semicolon-separated compact format

## Project Structure

```
src/tknpack/
    __init__.py              # Public API: encode(), decode()
    ai.py                    # TokenPackModel for pydantic-ai
    core/
        __init__.py           # Re-exports
        codec.py              # Unified Codec class
        types.py              # Format, ToonOptions, PloonOptions
        errors.py             # Error types
        toon/
            encoder.py        # TOON encoder
            decoder.py        # TOON decoder
        ploon/
            schema.py         # PLOON schema builder/parser
            encoder.py        # PLOON encoder
            decoder.py        # PLOON decoder
```

## Development

### Setup

```bash
git clone https://github.com/bigbag/tknpack.git
cd tknpack
make venv/create
make venv/install/all
```

### Commands

```bash
make test     # Run tests with coverage
make lint     # Run ruff + mypy
make format   # Format code with ruff
make clean    # Clean cache and build files
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov=tknpack --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_ploon_encoder.py -v

# Run specific test class or method
uv run pytest tests/test_encoder.py::TestFlatObjects -v
uv run pytest tests/test_decoder.py::TestRoundTrip::test_simple_object -v
```

## API Reference

### `encode(model, options=None, *, format=Format.TOON) -> str`

Encode a Pydantic model to TOON or PLOON format.

### `decode(text, model_class, *, format=Format.TOON) -> T`

Decode a TOON or PLOON string back to a Pydantic model.

### `Codec(format=Format.TOON, options=None)`

Unified encoder/decoder for raw Python dicts and lists.

### `TokenPackModel(wrapped, *, format=Format.TOON, options=None)`

pydantic-ai model wrapper that encodes tool results automatically.

## License

MIT License - see [LICENSE](LICENSE) file.
