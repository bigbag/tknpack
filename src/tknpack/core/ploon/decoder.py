"""PLOON decoder: PLOON string → Python objects."""

from __future__ import annotations

import re

from tknpack.core.errors import PloonDecodeError
from tknpack.core.ploon.schema import SchemaNode, parse_schema
from tknpack.core.types import PloonOptions

_ARRAY_PATH_RE = re.compile(r"^(\d+):(\d+)$")
_OBJECT_PATH_RE = re.compile(r"^(\d+) $")


def ploon_decode(
    text: str,
    options: PloonOptions | None = None,
) -> dict | list | str | int | float | bool | None:
    opts = options or PloonOptions()

    text = text.strip()
    if not text:
        return {}

    # Detect format: compact uses ';' as record separator
    if opts.compact or ("\n" not in text and ";" in text):
        parts = _split_respecting_escapes(text, ";")
        schema_line = parts[0].strip()
        data_lines = [p.strip() for p in parts[1:] if p.strip()]
    else:
        raw_lines = text.split("\n")
        schema_line = ""
        data_lines = []
        found_schema = False
        for line in raw_lines:
            stripped = line.strip()
            if not found_schema:
                if stripped:
                    schema_line = stripped
                    found_schema = True
            elif stripped:
                data_lines.append(stripped)

    # Check if this is a schema line
    if not schema_line.startswith("["):
        # Not a PLOON schema — might be a bare primitive
        return _parse_primitive(schema_line)

    root_name, count, schema_tree = parse_schema(schema_line)

    if schema_tree.kind == "primitive_array":
        # Root-level primitive array
        if not data_lines:
            return []
        vals = _split_primitive_array(data_lines[0])
        return [_parse_primitive(v) for v in vals]

    if count == 0:
        return {root_name: []} if root_name else []

    # Parse data lines into path-indexed records
    parsed_lines = _parse_data_lines(data_lines, opts)

    # Reconstruct the data structure
    result = _reconstruct(parsed_lines, schema_tree, 1)

    if root_name:
        return {root_name: result}
    return result


def _parse_data_lines(
    data_lines: list[str],
    opts: PloonOptions,
) -> list[tuple[int, int | None, list[str]]]:
    """Parse data lines into (depth, index_or_None, values) tuples."""
    result: list[tuple[int, int | None, list[str]]] = []
    delim = opts.field_delimiter

    for line in data_lines:
        # Find the first delimiter to split path from values
        first_delim = _find_first_unescaped(line, delim)
        if first_delim == -1:
            # Line with only a path and no values
            path_str = line
            values: list[str] = []
        else:
            path_str = line[:first_delim]
            values_str = line[first_delim + len(delim) :]
            values = _split_values(values_str, delim)

        # Parse the path — don't strip trailing space (object paths use "depth ")
        arr_match = _ARRAY_PATH_RE.match(path_str.strip())
        if arr_match:
            depth = int(arr_match.group(1))
            index = int(arr_match.group(2))
            result.append((depth, index, values))
            continue

        obj_match = _OBJECT_PATH_RE.match(path_str)
        if obj_match:
            depth = int(obj_match.group(1))
            result.append((depth, None, values))
            continue

        # Try parsing as just a number (object path without trailing space)
        stripped = path_str.strip()
        if stripped.isdigit():
            result.append((int(stripped), None, values))
            continue

        raise PloonDecodeError(f"Invalid path prefix: {path_str!r}")

    return result


def _reconstruct(
    parsed_lines: list[tuple[int, int | None, list[str]]],
    schema: SchemaNode,
    base_depth: int,
) -> list:
    """Reconstruct array data from parsed lines using the schema tree."""
    result: list[dict] = []
    i = 0

    while i < len(parsed_lines):
        depth, index, values = parsed_lines[i]

        if depth < base_depth:
            break

        if depth == base_depth and index is not None:
            # This is an array element at our expected depth
            obj: dict = {}

            # Map primitive fields from values
            val_idx = 0
            for child in schema.children:
                if child.kind == "field":
                    if val_idx < len(values):
                        obj[child.name] = _parse_primitive(values[val_idx])
                    else:
                        obj[child.name] = None
                    val_idx += 1
                elif child.kind == "primitive_array":
                    if val_idx < len(values):
                        raw = values[val_idx]
                        prim_vals = _split_primitive_array(raw)
                        obj[child.name] = [_parse_primitive(v) for v in prim_vals]
                    else:
                        obj[child.name] = []
                    val_idx += 1

            # Now consume following lines for nested structures
            i += 1
            for child in schema.children:
                if child.kind == "object":
                    if i < len(parsed_lines):
                        next_depth, next_index, next_values = parsed_lines[i]
                        if next_depth == base_depth + 1 and next_index is None:
                            nested_obj = _reconstruct_object(next_values, child, parsed_lines, i, opts_depth=next_depth)
                            obj[child.name] = nested_obj
                            i += 1
                            # Consume deeper object lines
                            while i < len(parsed_lines):
                                nd, ni, _ = parsed_lines[i]
                                if nd > next_depth and ni is None:
                                    i += 1
                                else:
                                    break
                        else:
                            obj[child.name] = {}
                    else:
                        obj[child.name] = {}
                elif child.kind == "array":
                    # Collect nested array elements
                    sub_lines: list[tuple[int, int | None, list[str]]] = []
                    while i < len(parsed_lines):
                        nd, ni, nv = parsed_lines[i]
                        if nd >= base_depth + 1 and not (nd == base_depth and ni is not None):
                            sub_lines.append((nd, ni, nv))
                            i += 1
                        else:
                            break
                    if sub_lines:
                        nested_items = _reconstruct(sub_lines, child, base_depth + 1)
                    obj[child.name] = nested_items

            result.append(obj)
        else:
            i += 1

    return result


def _reconstruct_object(
    values: list[str],
    schema: SchemaNode,
    parsed_lines: list[tuple[int, int | None, list[str]]],
    line_idx: int,
    opts_depth: int,
) -> dict:
    """Reconstruct a nested object from its values line."""
    obj: dict = {}
    val_idx = 0

    for child in schema.children:
        if child.kind == "field":
            if val_idx < len(values):
                obj[child.name] = _parse_primitive(values[val_idx])
            else:
                obj[child.name] = None
            val_idx += 1
        elif child.kind == "primitive_array":
            if val_idx < len(values):
                raw = values[val_idx]
                prim_vals = _split_primitive_array(raw)
                obj[child.name] = [_parse_primitive(v) for v in prim_vals]
            else:
                obj[child.name] = []
            val_idx += 1
        elif child.kind == "object":
            obj[child.name] = {}
        elif child.kind == "array":
            obj[child.name] = []

    return obj


def _find_first_unescaped(text: str, ch: str) -> int:
    """Find the first unescaped occurrence of ch in text."""
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            i += 2
            continue
        if text[i : i + len(ch)] == ch:
            return i
        i += 1
    return -1


def _split_values(text: str, delimiter: str) -> list[str]:
    """Split a values string by delimiter, respecting backslash escapes."""
    parts: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            current.append(text[i])
            current.append(text[i + 1])
            i += 2
        elif text[i : i + len(delimiter)] == delimiter:
            parts.append("".join(current))
            current = []
            i += len(delimiter)
        else:
            current.append(text[i])
            i += 1
    parts.append("".join(current))
    return parts


def _split_primitive_array(text: str) -> list[str]:
    """Split comma-separated primitive array values, respecting \\, escapes."""
    parts: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            current.append(text[i])
            current.append(text[i + 1])
            i += 2
        elif text[i] == ",":
            parts.append("".join(current))
            current = []
            i += 1
        else:
            current.append(text[i])
            i += 1
    parts.append("".join(current))
    return parts


def _split_respecting_escapes(text: str, sep: str) -> list[str]:
    """Split text by sep, respecting backslash escapes."""
    parts: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            current.append(text[i])
            current.append(text[i + 1])
            i += 2
        elif text[i] == sep:
            parts.append("".join(current))
            current = []
            i += 1
        else:
            current.append(text[i])
            i += 1
    parts.append("".join(current))
    return parts


def _unescape(value: str) -> str:
    """Remove PLOON backslash escapes from a value string."""
    result: list[str] = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            result.append(value[i + 1])
            i += 2
        else:
            result.append(value[i])
            i += 1
    return "".join(result)


def _parse_primitive(value: str) -> str | int | float | bool | None:
    """Parse a PLOON primitive value string to a Python type."""
    value = _unescape(value.strip())
    if not value:
        return ""
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        pass
    return value


# Utility functions


def ploon_minify(text: str) -> str:
    """Convert standard PLOON (newline-separated) to compact (semicolon-separated)."""
    lines = text.split("\n")
    non_empty = [line.strip() for line in lines if line.strip()]
    return ";".join(non_empty)


def ploon_prettify(text: str) -> str:
    """Convert compact PLOON (semicolon-separated) to standard (newline-separated)."""
    parts = _split_respecting_escapes(text, ";")
    if not parts:
        return text
    # First part is the schema, add blank line after it
    result = [parts[0]]
    if len(parts) > 1:
        result.append("")
        result.extend(parts[1:])
    return "\n".join(result)


def ploon_is_valid(text: str, options: PloonOptions | None = None) -> bool:
    """Return True if the text is valid PLOON."""
    try:
        ploon_decode(text, options)
        return True
    except (PloonDecodeError, Exception):
        return False
