"""Tests for the TOON v3.0 decoder."""

import pytest

from tknpack.core import ToonDecodeError, toon_decode, toon_encode


class TestRoundTrip:
    """Verify toon_decode(toon_encode(data)) == data for various structures."""

    def test_flat_object(self):
        data = {"id": 123, "name": "Ada", "active": True}
        assert toon_decode(toon_encode(data)) == data

    def test_nested_object(self):
        data = {"user": {"id": 123, "name": "Ada"}}
        assert toon_decode(toon_encode(data)) == data

    def test_deep_nesting(self):
        data = {"a": {"b": {"c": "deep"}}}
        assert toon_decode(toon_encode(data)) == data

    def test_primitive_array(self):
        data = {"tags": ["admin", "ops", "dev"]}
        assert toon_decode(toon_encode(data)) == data

    def test_int_array(self):
        data = {"nums": [1, 2, 3]}
        assert toon_decode(toon_encode(data)) == data

    def test_mixed_primitive_array(self):
        data = {"mix": [1, "hello", True, None]}
        assert toon_decode(toon_encode(data)) == data

    def test_empty_array(self):
        data = {"items": []}
        assert toon_decode(toon_encode(data)) == data

    def test_tabular_array(self):
        data = {
            "items": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False},
            ]
        }
        assert toon_decode(toon_encode(data)) == data

    def test_non_uniform_dicts(self):
        data = {"items": [{"a": 1}, {"b": 2}]}
        assert toon_decode(toon_encode(data)) == data

    def test_null_values(self):
        data = {"x": None, "y": "hello"}
        assert toon_decode(toon_encode(data)) == data

    def test_booleans(self):
        data = {"a": True, "b": False}
        assert toon_decode(toon_encode(data)) == data

    def test_empty_object(self):
        assert toon_decode(toon_encode({})) == {}

    def test_empty_string_value(self):
        data = {"name": ""}
        assert toon_decode(toon_encode(data)) == data

    def test_string_with_colon(self):
        data = {"url": "http://example.com"}
        assert toon_decode(toon_encode(data)) == data

    def test_unicode(self):
        data = {"msg": "Hello 世界 👋"}
        assert toon_decode(toon_encode(data)) == data

    def test_object_with_multiple_types(self):
        data = {
            "name": "test",
            "count": 42,
            "active": True,
            "tags": ["a", "b"],
        }
        assert toon_decode(toon_encode(data)) == data


class TestDecoderSpecific:
    def test_empty_input(self):
        assert toon_decode("") == {}

    def test_whitespace_only(self):
        assert toon_decode("   ") == {}

    def test_single_primitive_string(self):
        assert toon_decode("hello") == "hello"

    def test_single_primitive_number(self):
        assert toon_decode("42") == 42

    def test_single_primitive_bool(self):
        assert toon_decode("true") is True

    def test_single_primitive_null(self):
        assert toon_decode("null") is None

    def test_root_primitive_array(self):
        result = toon_decode("[3]: 1,2,3")
        assert result == [1, 2, 3]

    def test_root_empty_array(self):
        result = toon_decode("[0]:")
        assert result == []

    def test_root_tabular_array(self):
        text = "[2]{id,name}:\n  1,A\n  2,B"
        result = toon_decode(text)
        assert result == [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

    def test_quoted_string_value(self):
        result = toon_decode('name: "true"')
        assert result == {"name": "true"}

    def test_quoted_string_with_escapes(self):
        result = toon_decode('text: "line1\\nline2"')
        assert result == {"text": "line1\nline2"}

    def test_leading_zero_as_string(self):
        result = toon_decode('code: "05"')
        assert result == {"code": "05"}

    def test_nested_empty_object(self):
        result = toon_decode("parent:")
        assert result == {"parent": {}}

    def test_invalid_escape_sequence(self):
        with pytest.raises(ToonDecodeError):
            toon_decode('x: "bad\\x"')

    def test_arrays_of_arrays(self):
        data = {"pairs": [[1, 2], [3, 4]]}
        assert toon_decode(toon_encode(data)) == data

    def test_quoted_key(self):
        result = toon_decode('"my-key": value')
        assert result == {"my-key": "value"}

    def test_float_round_trip(self):
        data = {"x": 3.14}
        assert toon_decode(toon_encode(data)) == data

    def test_negative_number(self):
        data = {"x": -7}
        assert toon_decode(toon_encode(data)) == data


class TestHikesExample:
    def test_full_round_trip(self):
        data = {
            "context": {
                "task": "Our favorite hikes together",
                "location": "Boulder",
            },
            "friends": ["ana", "luis", "sam"],
            "hikes": [
                {
                    "id": 1,
                    "name": "Blue Lake Trail",
                    "distanceKm": 7.5,
                    "elevationGain": 320,
                    "companion": "ana",
                    "wasSunny": True,
                },
                {
                    "id": 2,
                    "name": "Ridge Overlook",
                    "distanceKm": 9.2,
                    "elevationGain": 540,
                    "companion": "luis",
                    "wasSunny": False,
                },
                {
                    "id": 3,
                    "name": "Wildflower Loop",
                    "distanceKm": 5.1,
                    "elevationGain": 180,
                    "companion": "sam",
                    "wasSunny": True,
                },
            ],
        }
        assert toon_decode(toon_encode(data)) == data
