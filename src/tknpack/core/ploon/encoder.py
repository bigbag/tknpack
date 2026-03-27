"""PLOON encoder: Python objects → PLOON string."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from tknpack.core.errors import PloonEncodeError
from tknpack.core.ploon.schema import SchemaNode, build_schema
from tknpack.core.types import PloonOptions


def ploon_encode(
    data: dict | list | str | int | float | bool | None,
    options: PloonOptions | None = None,
) -> str:
    opts = options or PloonOptions()

    # Primitives pass through directly
    if data is None or isinstance(data, (str, int, float, bool)):
        return _encode_primitive(data, opts)

    if not isinstance(data, (Mapping, Sequence)) or isinstance(data, (str, bytes)):
        raise PloonEncodeError(f"Cannot encode {type(data).__name__}")

    schema_str, schema_tree = build_schema(data)
    lines: list[str] = []
    _emit_data(data, schema_tree, 1, lines, opts)

    record_sep = ";" if opts.compact else "\n"
    data_part = record_sep.join(lines)

    if opts.compact:
        return f"{schema_str};{data_part}"
    return f"{schema_str}\n\n{data_part}"


def _emit_data(
    data: dict | list,
    schema: SchemaNode,
    depth: int,
    lines: list[str],
    opts: PloonOptions,
) -> None:
    if isinstance(data, Mapping):
        # Root is a dict — check for single-key array shortcut
        keys = list(data.keys())
        if len(keys) == 1 and isinstance(data[keys[0]], list):
            _emit_array(data[keys[0]], schema, depth, lines, opts)
        else:
            # Flat dict treated as single-record
            _emit_object_record(data, schema, depth, 1, lines, opts)
    elif isinstance(data, list):
        _emit_array(data, schema, depth, lines, opts)


def _emit_array(
    arr: list,
    schema: SchemaNode,
    depth: int,
    lines: list[str],
    opts: PloonOptions,
) -> None:
    if schema.kind == "primitive_array":
        # Primitive root array — single line of comma-separated values
        vals = ",".join(_escape_primitive_array_value(v, opts) for v in arr)
        lines.append(vals)
        return

    for idx, item in enumerate(arr, start=1):
        if isinstance(item, Mapping):
            _emit_object_record(item, schema, depth, idx, lines, opts)
        else:
            # Primitive in a typed array slot
            path = f"{depth}{opts.path_separator}{idx}"
            lines.append(f"{path}{opts.field_delimiter}{_encode_primitive(item, opts)}")


def _emit_object_record(
    obj: Mapping,
    schema: SchemaNode,
    depth: int,
    index: int,
    lines: list[str],
    opts: PloonOptions,
) -> None:
    """Emit data lines for a single object record within an array."""
    delim = opts.field_delimiter
    sep = opts.path_separator

    # Collect primitive and primitive-array fields for the main record line
    main_values: list[str] = []
    deferred: list[tuple[SchemaNode, object]] = []

    for child in schema.children:
        value = obj.get(child.name)

        if child.kind == "field":
            main_values.append(_encode_primitive(value, opts))
        elif child.kind == "primitive_array":
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                prim_vals = ",".join(_escape_primitive_array_value(v, opts) for v in value)
                main_values.append(prim_vals)
            else:
                main_values.append(_encode_primitive(value, opts))
        elif child.kind in ("array", "object"):
            deferred.append((child, value))

    # Emit the main record line: depth:index|val1|val2|...
    if main_values:
        path = f"{depth}{sep}{index}"
        lines.append(f"{path}{delim}{delim.join(main_values)}")

    # Emit deferred nested structures
    for child_schema, value in deferred:
        if child_schema.kind == "object" and isinstance(value, Mapping):
            _emit_nested_object(value, child_schema, depth + 1, lines, opts)
        elif child_schema.kind == "array" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for sub_idx, sub_item in enumerate(value, start=1):
                if isinstance(sub_item, Mapping):
                    _emit_object_record(sub_item, child_schema, depth + 1, sub_idx, lines, opts)
                else:
                    path = f"{depth + 1}{opts.path_separator}{sub_idx}"
                    lines.append(f"{path}{opts.field_delimiter}{_encode_primitive(sub_item, opts)}")


def _emit_nested_object(
    obj: Mapping,
    schema: SchemaNode,
    depth: int,
    lines: list[str],
    opts: PloonOptions,
) -> None:
    """Emit a nested object using depth-space notation."""
    delim = opts.field_delimiter

    main_values: list[str] = []
    deferred: list[tuple[SchemaNode, object]] = []

    for child in schema.children:
        value = obj.get(child.name)

        if child.kind == "field":
            main_values.append(_encode_primitive(value, opts))
        elif child.kind == "primitive_array":
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                prim_vals = ",".join(_escape_primitive_array_value(v, opts) for v in value)
                main_values.append(prim_vals)
            else:
                main_values.append(_encode_primitive(value, opts))
        elif child.kind in ("array", "object"):
            deferred.append((child, value))

    # Object path: "depth " (depth followed by space)
    if main_values:
        lines.append(f"{depth} {delim}{delim.join(main_values)}")

    for child_schema, value in deferred:
        if child_schema.kind == "object" and isinstance(value, Mapping):
            _emit_nested_object(value, child_schema, depth + 1, lines, opts)
        elif child_schema.kind == "array" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for sub_idx, sub_item in enumerate(value, start=1):
                if isinstance(sub_item, Mapping):
                    _emit_object_record(sub_item, child_schema, depth + 1, sub_idx, lines, opts)


def _encode_primitive(value: object, opts: PloonOptions) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_number(value)
    if isinstance(value, str):
        return _escape_value(value, opts)
    raise PloonEncodeError(f"Cannot encode {type(value).__name__} as a PLOON primitive")


def _format_number(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        return "null"
    if value == 0.0 and math.copysign(1.0, value) < 0:
        return "0"
    if value == int(value) and not math.isinf(value):
        return str(int(value))
    result = repr(value)
    if "e" in result or "E" in result:
        result = f"{value:.20f}"
        result = result.rstrip("0").rstrip(".")
    return result


def _escape_value(value: str, opts: PloonOptions) -> str:
    """Escape special characters in a PLOON value using backslash escaping."""
    result: list[str] = []
    for ch in value:
        if ch == "\\":
            result.append("\\\\")
        elif ch == opts.field_delimiter:
            result.append(f"\\{ch}")
        elif ch == ";":
            result.append("\\;")
        else:
            result.append(ch)
    return "".join(result)


def _escape_primitive_array_value(value: object, opts: PloonOptions) -> str:
    """Escape a value for inline primitive arrays (comma-separated)."""
    prim = _encode_primitive(value, opts)
    # Additionally escape commas for inline arrays
    return prim.replace(",", "\\,")
