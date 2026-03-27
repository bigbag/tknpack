"""Tests for the TOON v3.0 encoder."""

from tknpack.core import ToonOptions, toon_encode


class TestFlatObjects:
    def test_simple_object(self):
        data = {"id": 123, "name": "Ada", "active": True}
        result = toon_encode(data)
        assert result == "id: 123\nname: Ada\nactive: true"

    def test_empty_object(self):
        assert toon_encode({}) == ""

    def test_single_field(self):
        assert toon_encode({"key": "value"}) == "key: value"

    def test_null_value(self):
        assert toon_encode({"x": None}) == "x: null"

    def test_boolean_values(self):
        result = toon_encode({"a": True, "b": False})
        assert result == "a: true\nb: false"


class TestNestedObjects:
    def test_one_level_nesting(self):
        data = {"user": {"id": 123, "name": "Ada"}}
        result = toon_encode(data)
        assert result == "user:\n  id: 123\n  name: Ada"

    def test_deep_nesting(self):
        data = {"a": {"b": {"c": "deep"}}}
        result = toon_encode(data)
        assert result == "a:\n  b:\n    c: deep"

    def test_mixed_nesting(self):
        data = {"name": "root", "child": {"id": 1, "value": "x"}}
        result = toon_encode(data)
        assert result == "name: root\nchild:\n  id: 1\n  value: x"

    def test_empty_nested_object(self):
        data = {"parent": {}}
        result = toon_encode(data)
        assert result == "parent:"


class TestPrimitiveArrays:
    def test_string_array(self):
        data = {"tags": ["admin", "ops", "dev"]}
        result = toon_encode(data)
        assert result == "tags[3]: admin,ops,dev"

    def test_int_array(self):
        data = {"nums": [1, 2, 3]}
        result = toon_encode(data)
        assert result == "nums[3]: 1,2,3"

    def test_mixed_primitive_array(self):
        data = {"mix": [1, "hello", True, None]}
        result = toon_encode(data)
        assert result == "mix[4]: 1,hello,true,null"

    def test_empty_array(self):
        data = {"items": []}
        result = toon_encode(data)
        assert result == "items[0]:"

    def test_single_element_array(self):
        data = {"x": [42]}
        result = toon_encode(data)
        assert result == "x[1]: 42"


class TestTabularArrays:
    def test_simple_tabular(self):
        data = {
            "items": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False},
            ]
        }
        result = toon_encode(data)
        expected = "items[2]{id,name,active}:\n  1,Alice,true\n  2,Bob,false"
        assert result == expected

    def test_single_row_tabular(self):
        data = {"items": [{"a": 1, "b": 2}]}
        result = toon_encode(data)
        assert result == "items[1]{a,b}:\n  1,2"

    def test_tabular_with_null(self):
        data = {
            "items": [
                {"x": 1, "y": None},
                {"x": 2, "y": 3},
            ]
        }
        result = toon_encode(data)
        assert result == "items[2]{x,y}:\n  1,null\n  2,3"


class TestMixedArrays:
    def test_objects_in_list(self):
        data = {
            "items": [
                {"id": 1, "name": "First"},
                {"id": 2, "name": "Second"},
            ]
        }
        # This is tabular since all dicts have same keys
        result = toon_encode(data)
        assert "items[2]{id,name}:" in result

    def test_mixed_types(self):
        data = {"items": [1, "text", {"key": "val"}]}
        result = toon_encode(data)
        assert "items[3]:" in result
        assert "- 1" in result
        assert "- text" in result
        assert "- key: val" in result

    def test_non_uniform_dicts(self):
        data = {
            "items": [
                {"a": 1},
                {"b": 2},
            ]
        }
        result = toon_encode(data)
        assert "items[2]:" in result
        assert "- a: 1" in result
        assert "- b: 2" in result


class TestArraysOfArrays:
    def test_primitive_arrays_of_arrays(self):
        data = {"pairs": [[1, 2], [3, 4]]}
        result = toon_encode(data)
        assert "pairs[2]:" in result
        assert "- [2]: 1,2" in result
        assert "- [2]: 3,4" in result


class TestStringQuoting:
    def test_empty_string(self):
        data = {"name": ""}
        result = toon_encode(data)
        assert result == 'name: ""'

    def test_reserved_true(self):
        data = {"val": "true"}
        result = toon_encode(data)
        assert result == 'val: "true"'

    def test_reserved_false(self):
        data = {"val": "false"}
        result = toon_encode(data)
        assert result == 'val: "false"'

    def test_reserved_null(self):
        data = {"val": "null"}
        result = toon_encode(data)
        assert result == 'val: "null"'

    def test_numeric_like_string(self):
        data = {"version": "123"}
        result = toon_encode(data)
        assert result == 'version: "123"'

    def test_leading_zero_string(self):
        data = {"code": "05"}
        result = toon_encode(data)
        assert result == 'code: "05"'

    def test_structural_chars_colon(self):
        data = {"url": "http://example.com"}
        result = toon_encode(data)
        assert result == 'url: "http://example.com"'

    def test_structural_chars_brackets(self):
        data = {"expr": "[1]"}
        result = toon_encode(data)
        assert result == 'expr: "[1]"'

    def test_contains_delimiter(self):
        data = {"csv": "a,b,c"}
        result = toon_encode(data)
        assert result == 'csv: "a,b,c"'

    def test_leading_whitespace(self):
        data = {"x": " hello"}
        result = toon_encode(data)
        assert result == 'x: " hello"'

    def test_trailing_whitespace(self):
        data = {"x": "hello "}
        result = toon_encode(data)
        assert result == 'x: "hello "'

    def test_leading_hyphen(self):
        data = {"x": "-abc"}
        result = toon_encode(data)
        assert result == 'x: "-abc"'

    def test_bare_hyphen(self):
        data = {"x": "-"}
        result = toon_encode(data)
        assert result == 'x: "-"'

    def test_unicode_no_quoting(self):
        data = {"message": "Hello 世界 👋"}
        result = toon_encode(data)
        assert result == "message: Hello 世界 👋"

    def test_newline_requires_quoting(self):
        data = {"text": "line1\nline2"}
        result = toon_encode(data)
        assert result == 'text: "line1\\nline2"'

    def test_tab_requires_quoting(self):
        data = {"text": "col1\tcol2"}
        result = toon_encode(data)
        assert result == 'text: "col1\\tcol2"'

    def test_backslash_escape(self):
        data = {"path": "C:\\Users"}
        result = toon_encode(data)
        assert result == 'path: "C:\\\\Users"'

    def test_quote_in_string(self):
        data = {"text": 'say "hello"'}
        result = toon_encode(data)
        assert result == 'text: "say \\"hello\\""'

    def test_plain_string_no_quoting(self):
        data = {"name": "Alice Smith"}
        result = toon_encode(data)
        assert result == "name: Alice Smith"

    def test_negative_numeric_string(self):
        data = {"x": "-5"}
        result = toon_encode(data)
        assert result == 'x: "-5"'


class TestKeyQuoting:
    def test_simple_key(self):
        data = {"name": "val"}
        result = toon_encode(data)
        assert result == "name: val"

    def test_underscore_key(self):
        data = {"my_key": "val"}
        result = toon_encode(data)
        assert result == "my_key: val"

    def test_dotted_key(self):
        data = {"some.key": "val"}
        result = toon_encode(data)
        assert result == "some.key: val"

    def test_hyphen_key_needs_quoting(self):
        data = {"my-key": "val"}
        result = toon_encode(data)
        assert result == '"my-key": val'

    def test_numeric_start_key(self):
        data = {"123abc": "val"}
        result = toon_encode(data)
        assert result == '"123abc": val'

    def test_space_in_key(self):
        data = {"my key": "val"}
        result = toon_encode(data)
        assert result == '"my key": val'


class TestNumberCanonicalization:
    def test_integer(self):
        assert toon_encode({"x": 42}) == "x: 42"

    def test_negative_integer(self):
        assert toon_encode({"x": -7}) == "x: -7"

    def test_zero(self):
        assert toon_encode({"x": 0}) == "x: 0"

    def test_float(self):
        assert toon_encode({"x": 3.14}) == "x: 3.14"

    def test_float_no_trailing_zeros(self):
        assert toon_encode({"x": 1.0}) == "x: 1"

    def test_negative_zero(self):
        assert toon_encode({"x": -0.0}) == "x: 0"

    def test_nan_to_null(self):
        assert toon_encode({"x": float("nan")}) == "x: null"

    def test_inf_to_null(self):
        assert toon_encode({"x": float("inf")}) == "x: null"

    def test_neg_inf_to_null(self):
        assert toon_encode({"x": float("-inf")}) == "x: null"

    def test_large_number_no_exponent(self):
        assert toon_encode({"x": 1000000}) == "x: 1000000"

    def test_small_float(self):
        result = toon_encode({"x": 0.5})
        assert result == "x: 0.5"


class TestIndentation:
    def test_custom_indent(self):
        data = {"a": {"b": "c"}}
        result = toon_encode(data, ToonOptions(indent=4))
        assert result == "a:\n    b: c"

    def test_default_indent(self):
        data = {"a": {"b": "c"}}
        result = toon_encode(data)
        assert result == "a:\n  b: c"


class TestDelimiters:
    def test_tab_delimiter(self):
        data = {"tags": ["a", "b", "c"]}
        result = toon_encode(data, ToonOptions(delimiter="\t"))
        assert result == "tags[3\t]: a\tb\tc"

    def test_pipe_delimiter(self):
        data = {"tags": ["a", "b", "c"]}
        result = toon_encode(data, ToonOptions(delimiter="|"))
        assert result == "tags[3|]: a|b|c"

    def test_tab_delimiter_tabular(self):
        data = {"items": [{"a": 1, "b": 2}, {"a": 3, "b": 4}]}
        result = toon_encode(data, ToonOptions(delimiter="\t"))
        assert "items[2\t]{a\tb}:" in result
        assert "1\t2" in result


class TestRootArrays:
    def test_root_primitive_array(self):
        result = toon_encode([1, 2, 3])
        assert result == "[3]: 1,2,3"

    def test_root_empty_array(self):
        result = toon_encode([])
        assert result == "[0]:"

    def test_root_tabular_array(self):
        data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        result = toon_encode(data)
        assert "[2]{id,name}:" in result
        assert "  1,A" in result
        assert "  2,B" in result

    def test_root_mixed_array(self):
        data = [1, "text", {"key": "val"}]
        result = toon_encode(data)
        assert "[3]:" in result
        assert "- 1" in result


class TestRootPrimitives:
    def test_root_string(self):
        assert toon_encode("hello") == "hello"

    def test_root_number(self):
        assert toon_encode(42) == "42"

    def test_root_bool(self):
        assert toon_encode(True) == "true"

    def test_root_null(self):
        assert toon_encode(None) == "null"

    def test_root_string_needing_quotes(self):
        assert toon_encode("true") == '"true"'


class TestComplexStructures:
    def test_hikes_example(self):
        """Test the example from the TOON spec."""
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
        result = toon_encode(data)
        assert "context:" in result
        assert "  task: Our favorite hikes together" in result
        assert "  location: Boulder" in result
        assert "friends[3]: ana,luis,sam" in result
        assert "hikes[3]{id,name,distanceKm,elevationGain,companion,wasSunny}:" in result
        assert "  1,Blue Lake Trail,7.5,320,ana,true" in result
        assert "  3,Wildflower Loop,5.1,180,sam,true" in result

    def test_object_with_multiple_arrays(self):
        data = {
            "name": "test",
            "tags": ["a", "b"],
            "items": [{"x": 1}, {"x": 2}],
        }
        result = toon_encode(data)
        assert "name: test" in result
        assert "tags[2]: a,b" in result
        assert "items[2]{x}:" in result
