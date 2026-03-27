"""Tests for the PLOON encoder."""

from tknpack.core.ploon import ploon_encode
from tknpack.core.types import PloonOptions


class TestSimpleArrays:
    def test_products_example(self):
        """The canonical example from ploon.ai."""
        data = {"products": [{"id": 1, "name": "Shirt", "price": 29.99}, {"id": 2, "name": "Pants", "price": 49.99}]}
        result = ploon_encode(data)
        lines = result.split("\n")
        assert lines[0] == "[products#2](id,name,price)"
        assert lines[1] == ""
        assert lines[2] == "1:1|1|Shirt|29.99"
        assert lines[3] == "1:2|2|Pants|49.99"

    def test_single_item_array(self):
        data = {"items": [{"id": 1, "name": "Book"}]}
        result = ploon_encode(data)
        lines = result.split("\n")
        assert lines[0] == "[items#1](id,name)"
        assert lines[2] == "1:1|1|Book"

    def test_empty_array(self):
        data = {"items": []}
        result = ploon_encode(data)
        assert "[items#0]()" in result


class TestNestedArrays:
    def test_nested_array_of_objects(self):
        data = {
            "products": [
                {
                    "id": 1,
                    "name": "T-Shirt",
                    "colors": [{"name": "Red", "hex": "#FF0000"}, {"name": "Blue", "hex": "#0000FF"}],
                }
            ]
        }
        result = ploon_encode(data)
        lines = result.split("\n")
        assert "[products#1]" in lines[0]
        assert "colors#(name,hex)" in lines[0]
        # Main record line has id and name
        assert "1:1|1|T-Shirt" in lines[2]
        # Nested color records at depth 2
        assert "2:1|Red|#FF0000" in lines[3]
        assert "2:2|Blue|#0000FF" in lines[4]


class TestNestedObjects:
    def test_nested_object(self):
        data = {
            "orders": [
                {
                    "id": 1001,
                    "date": "2024-01-15",
                    "customer": {"id": "CUST-001", "name": "Alice Johnson"},
                }
            ]
        }
        result = ploon_encode(data)
        lines = result.split("\n")
        assert "customer{id,name}" in lines[0]
        # Main record: date, id
        assert "1:1" in lines[2]
        # Nested object at depth 2
        found_customer = False
        for line in lines[2:]:
            if "2 |" in line and "CUST-001" in line:
                found_customer = True
        assert found_customer

    def test_deeply_nested_object(self):
        data = {
            "orders": [
                {
                    "id": 1001,
                    "customer": {
                        "name": "Alice",
                        "address": {"city": "New York", "zip": "10001"},
                    },
                }
            ]
        }
        result = ploon_encode(data)
        assert "customer{name,address{city,zip}}" in result or "customer{address{city,zip},name}" in result


class TestPrimitiveArrays:
    def test_inline_primitive_array(self):
        data = {"items": [{"tags": ["python", "ai", "llm"], "name": "pkg"}]}
        result = ploon_encode(data)
        assert "tags#()" in result
        # Primitive array values are comma-separated inline
        assert "python,ai,llm" in result

    def test_primitive_array_with_commas(self):
        data = {"items": [{"coords": ["40.7128,74.0060", "34.0522,118.2437"]}]}
        result = ploon_encode(data)
        # Commas within values must be escaped
        assert "40.7128\\,74.0060" in result


class TestPrimitiveValues:
    def test_null(self):
        data = {"items": [{"id": 1, "name": None}]}
        result = ploon_encode(data)
        assert "null" in result

    def test_booleans(self):
        data = {"items": [{"active": True, "deleted": False}]}
        result = ploon_encode(data)
        assert "true" in result
        assert "false" in result

    def test_primitive_passthrough(self):
        assert ploon_encode(42) == "42"
        assert ploon_encode("hello") == "hello"
        assert ploon_encode(None) == "null"
        assert ploon_encode(True) == "true"


class TestEscaping:
    def test_pipe_in_value(self):
        data = {"items": [{"text": "hello|world"}]}
        result = ploon_encode(data)
        assert "hello\\|world" in result

    def test_backslash_in_value(self):
        data = {"items": [{"path": "a\\b"}]}
        result = ploon_encode(data)
        assert "a\\\\b" in result

    def test_semicolon_in_value(self):
        data = {"items": [{"text": "a;b"}]}
        result = ploon_encode(data)
        assert "a\\;b" in result


class TestCompactFormat:
    def test_compact_output(self):
        data = {"items": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}
        opts = PloonOptions(compact=True)
        result = ploon_encode(data, opts)
        assert "\n" not in result
        assert ";" in result
        assert result.startswith("[items#2](id,name);")


class TestFlatDict:
    def test_flat_dict_as_single_record(self):
        data = {"id": 1, "name": "Ada", "active": True}
        result = ploon_encode(data)
        assert "[root#1]" in result
        assert "1:1" in result
