"""Basic TOON and PLOON encoding examples."""

from tknpack.core import Codec, Format, PloonOptions, ToonOptions, toon_encode

# Simple object
data = {"id": 123, "name": "Ada Lovelace", "active": True}
print("=== Simple Object (TOON) ===")
print(toon_encode(data))
print()

# Nested object
data = {
    "user": {"id": 1, "name": "Ada"},
    "settings": {"theme": "dark", "lang": "en"},
}
print("=== Nested Object (TOON) ===")
print(toon_encode(data))
print()

# Primitive array
data = {"tags": ["python", "ai", "llm"]}
print("=== Primitive Array (TOON) ===")
print(toon_encode(data))
print()

# Tabular array (uniform dicts → compact CSV-like format)
data = {
    "users": [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
        {"id": 3, "name": "Carol", "role": "user"},
    ]
}
print("=== Tabular Array (TOON) ===")
print(toon_encode(data))
print()

# Custom indent
print("=== Custom Indent (4 spaces) ===")
print(toon_encode({"a": {"b": {"c": "deep"}}}, ToonOptions(indent=4)))
print()

# Pipe delimiter
print("=== Pipe Delimiter ===")
print(toon_encode({"items": ["x", "y", "z"]}, ToonOptions(delimiter="|")))
print()

# ── PLOON examples ──

# Using Codec for PLOON encoding
codec = Codec(Format.PLOON)
print("=== Tabular Array (PLOON) ===")
print(codec.encode(data))
print()

# Compact PLOON format
compact_codec = Codec(Format.PLOON, PloonOptions(compact=True))
print("=== Compact PLOON ===")
print(compact_codec.encode(data))
print()

# Nested arrays in PLOON
nested = {
    "products": [
        {
            "id": 1,
            "name": "T-Shirt",
            "colors": [{"name": "Red", "hex": "#FF0000"}, {"name": "Blue", "hex": "#0000FF"}],
        }
    ]
}
print("=== Nested Arrays (PLOON) ===")
print(codec.encode(nested))
