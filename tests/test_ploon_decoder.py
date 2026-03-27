"""Tests for the PLOON decoder and round-trip encoding/decoding."""

from tknpack.core.ploon import ploon_decode, ploon_encode, ploon_is_valid, ploon_minify, ploon_prettify
from tknpack.core.types import PloonOptions


class TestRoundTrip:
    def test_simple_array(self):
        data = {"products": [{"id": 1, "name": "Shirt", "price": 29.99}, {"id": 2, "name": "Pants", "price": 49.99}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_single_item(self):
        data = {"items": [{"id": 1, "name": "Book"}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_empty_array(self):
        data = {"items": []}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_nested_arrays(self):
        data = {
            "products": [
                {
                    "id": 1,
                    "name": "T-Shirt",
                    "colors": [{"name": "Red", "hex": "#FF0000"}, {"name": "Blue", "hex": "#0000FF"}],
                }
            ]
        }
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_null_values(self):
        data = {"items": [{"id": 1, "name": None}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_boolean_values(self):
        data = {"items": [{"active": True, "deleted": False}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_multiple_records(self):
        data = {
            "users": [
                {"id": 1, "name": "Alice", "score": 95.5},
                {"id": 2, "name": "Bob", "score": 87.3},
                {"id": 3, "name": "Carol", "score": 92.1},
            ]
        }
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data


class TestNestedObjectRoundTrip:
    def test_nested_object(self):
        data = {
            "orders": [
                {
                    "id": 1001,
                    "date": "2024-01-15",
                    "customer": {"id": "CUST-001", "name": "Alice"},
                }
            ]
        }
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data


class TestPrimitiveArrayRoundTrip:
    def test_inline_primitives(self):
        data = {"items": [{"name": "pkg", "tags": ["python", "ai", "llm"]}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data


class TestCompactRoundTrip:
    def test_compact_roundtrip(self):
        data = {"items": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}
        opts = PloonOptions(compact=True)
        encoded = ploon_encode(data, opts)
        decoded = ploon_decode(encoded, opts)
        assert decoded == data


class TestEscapingRoundTrip:
    def test_pipe_in_value(self):
        data = {"items": [{"text": "hello|world"}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_backslash_in_value(self):
        data = {"items": [{"path": "C:\\Users"}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data

    def test_semicolon_in_value(self):
        data = {"items": [{"text": "a;b"}]}
        encoded = ploon_encode(data)
        decoded = ploon_decode(encoded)
        assert decoded == data


class TestDecodeDirectly:
    def test_decode_products(self):
        ploon = "[products#2](id,name,price)\n\n1:1|1|Shirt|29.99\n1:2|2|Pants|49.99"
        result = ploon_decode(ploon)
        assert result == {
            "products": [{"id": 1, "name": "Shirt", "price": 29.99}, {"id": 2, "name": "Pants", "price": 49.99}]
        }

    def test_decode_empty(self):
        result = ploon_decode("")
        assert result == {}

    def test_decode_primitive(self):
        assert ploon_decode("42") == 42
        assert ploon_decode("hello") == "hello"


class TestUtilities:
    def test_minify(self):
        standard = "[items#2](id,name)\n\n1:1|1|A\n1:2|2|B"
        compact = ploon_minify(standard)
        assert "\n" not in compact
        assert ";" in compact

    def test_prettify(self):
        compact = "[items#2](id,name);1:1|1|A;1:2|2|B"
        standard = ploon_prettify(compact)
        assert "\n" in standard
        lines = standard.split("\n")
        assert lines[0] == "[items#2](id,name)"

    def test_is_valid(self):
        assert ploon_is_valid("[items#2](id,name)\n\n1:1|1|A\n1:2|2|B")
        assert ploon_is_valid("")  # empty is valid (returns {})

    def test_minify_prettify_roundtrip(self):
        standard = "[items#2](id,name)\n\n1:1|1|A\n1:2|2|B"
        minified = ploon_minify(standard)
        prettified = ploon_prettify(minified)
        # Both should decode to the same data
        assert ploon_decode(standard) == ploon_decode(prettified)
