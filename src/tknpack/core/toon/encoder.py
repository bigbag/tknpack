"""TOON v3.0 encoder: Python objects → TOON string."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence

from tknpack.core.errors import ToonEncodeError
from tknpack.core.types import ToonOptions

_UNQUOTED_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")
_LEADING_ZERO_RE = re.compile(r"^0\d+$")
_RESERVED = frozenset({"true", "false", "null"})

_ESCAPE_MAP = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def toon_encode(
    data: dict | list | str | int | float | bool | None,
    options: ToonOptions | None = None,
) -> str:
    opts = options or ToonOptions()
    if isinstance(data, Mapping):
        return _encode_object(data, 0, opts)
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        return _encode_root_array(data, opts)
    return _encode_primitive(data, opts.delimiter)


def _encode_object(obj: Mapping, depth: int, opts: ToonOptions) -> str:
    if not obj:
        return ""
    lines: list[str] = []
    prefix = " " * (depth * opts.indent)
    for key, value in obj.items():
        encoded_key = _encode_key(key)
        if isinstance(value, Mapping):
            if not value:
                lines.append(f"{prefix}{encoded_key}:")
            else:
                lines.append(f"{prefix}{encoded_key}:")
                lines.append(_encode_object(value, depth + 1, opts))
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            lines.append(_encode_array_field(encoded_key, value, depth, opts))
        else:
            lines.append(f"{prefix}{encoded_key}: {_encode_primitive(value, opts.delimiter)}")
    return "\n".join(lines)


def _encode_root_array(arr: Sequence, opts: ToonOptions) -> str:
    if not arr:
        return "[0]:"
    if _is_all_primitives(arr):
        vals = opts.delimiter.join(_encode_primitive(v, opts.delimiter) for v in arr)
        delim_sym = _delimiter_symbol(opts.delimiter)
        return f"[{len(arr)}{delim_sym}]: {vals}"
    if _is_tabular(arr):
        return _encode_root_tabular(arr, opts)
    return _encode_root_mixed(arr, opts)


def _encode_array_field(key: str, arr: Sequence, depth: int, opts: ToonOptions) -> str:
    prefix = " " * (depth * opts.indent)
    if not arr:
        return f"{prefix}{key}[0]:"
    if _is_all_primitives(arr):
        vals = opts.delimiter.join(_encode_primitive(v, opts.delimiter) for v in arr)
        delim_sym = _delimiter_symbol(opts.delimiter)
        return f"{prefix}{key}[{len(arr)}{delim_sym}]: {vals}"
    if _is_tabular(arr):
        return _encode_tabular_field(key, arr, depth, opts)
    return _encode_mixed_field(key, arr, depth, opts)


def _encode_tabular_field(key: str, arr: Sequence, depth: int, opts: ToonOptions) -> str:
    prefix = " " * (depth * opts.indent)
    row_prefix = " " * ((depth + 1) * opts.indent)
    fields = list(arr[0].keys())
    delim = opts.delimiter
    delim_sym = _delimiter_symbol(delim)
    field_names = delim.join(_encode_key(f) for f in fields)
    lines = [f"{prefix}{key}[{len(arr)}{delim_sym}]{{{field_names}}}:"]
    for item in arr:
        row_vals = delim.join(_encode_primitive(item[f], delim) for f in fields)
        lines.append(f"{row_prefix}{row_vals}")
    return "\n".join(lines)


def _encode_root_tabular(arr: Sequence, opts: ToonOptions) -> str:
    fields = list(arr[0].keys())
    delim = opts.delimiter
    delim_sym = _delimiter_symbol(delim)
    field_names = delim.join(_encode_key(f) for f in fields)
    prefix = " " * opts.indent
    lines = [f"[{len(arr)}{delim_sym}]{{{field_names}}}:"]
    for item in arr:
        row_vals = delim.join(_encode_primitive(item[f], delim) for f in fields)
        lines.append(f"{prefix}{row_vals}")
    return "\n".join(lines)


def _encode_mixed_field(key: str, arr: Sequence, depth: int, opts: ToonOptions) -> str:
    prefix = " " * (depth * opts.indent)
    lines = [f"{prefix}{key}[{len(arr)}]:"]
    for item in arr:
        lines.append(_encode_list_item(item, depth + 1, opts))
    return "\n".join(lines)


def _encode_root_mixed(arr: Sequence, opts: ToonOptions) -> str:
    lines = [f"[{len(arr)}]:"]
    for item in arr:
        lines.append(_encode_list_item(item, 1, opts))
    return "\n".join(lines)


def _encode_list_item(item: object, depth: int, opts: ToonOptions) -> str:
    prefix = " " * (depth * opts.indent)
    if isinstance(item, Mapping):
        if not item:
            return f"{prefix}-"
        entries = list(item.items())
        first_key = _encode_key(entries[0][0])
        first_val = entries[0][1]
        item_lines: list[str] = []
        if isinstance(first_val, Sequence) and not isinstance(first_val, (str, bytes)) and _is_tabular(first_val):
            item_lines.append(_encode_list_item_leading_tabular(first_key, first_val, depth, opts))
            for k, v in entries[1:]:
                ek = _encode_key(k)
                if isinstance(v, Mapping):
                    item_lines.append(f"{prefix}{ek}:")
                    if v:
                        item_lines.append(_encode_object(v, depth + 1, opts))
                elif isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
                    item_lines.append(_encode_array_field(ek, v, depth, opts))
                else:
                    item_lines.append(f"{prefix}{ek}: {_encode_primitive(v, opts.delimiter)}")
        else:
            if isinstance(first_val, Mapping):
                item_lines.append(f"{prefix}- {first_key}:")
                if first_val:
                    item_lines.append(_encode_object(first_val, depth + 2, opts))
            elif isinstance(first_val, Sequence) and not isinstance(first_val, (str, bytes)):
                item_lines.append(f"{prefix}- {_encode_array_field(first_key, first_val, 0, opts).strip()}")
            else:
                item_lines.append(f"{prefix}- {first_key}: {_encode_primitive(first_val, opts.delimiter)}")
            for k, v in entries[1:]:
                ek = _encode_key(k)
                if isinstance(v, Mapping):
                    item_lines.append(f"{prefix}  {ek}:")
                    if v:
                        item_lines.append(_encode_object(v, depth + 2, opts))
                elif isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
                    sub = _encode_array_field(ek, v, 0, opts).strip()
                    item_lines.append(f"{prefix}  {sub}")
                else:
                    item_lines.append(f"{prefix}  {ek}: {_encode_primitive(v, opts.delimiter)}")
        return "\n".join(item_lines)
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        if _is_all_primitives(item):
            delim = opts.delimiter
            delim_sym = _delimiter_symbol(delim)
            vals = delim.join(_encode_primitive(v, delim) for v in item)
            return f"{prefix}- [{len(item)}{delim_sym}]: {vals}"
        inner_lines = [f"{prefix}- [{len(item)}]:"]
        for sub in item:
            inner_lines.append(_encode_list_item(sub, depth + 1, opts))
        return "\n".join(inner_lines)
    return f"{prefix}- {_encode_primitive(item, opts.delimiter)}"


def _encode_list_item_leading_tabular(key: str, arr: Sequence, depth: int, opts: ToonOptions) -> str:
    prefix = " " * (depth * opts.indent)
    row_prefix = " " * ((depth + 1) * opts.indent)
    fields = list(arr[0].keys())
    delim = opts.delimiter
    delim_sym = _delimiter_symbol(delim)
    field_names = delim.join(_encode_key(f) for f in fields)
    lines = [f"{prefix}- {key}[{len(arr)}{delim_sym}]{{{field_names}}}:"]
    for item in arr:
        row_vals = delim.join(_encode_primitive(item[f], delim) for f in fields)
        lines.append(f"{row_prefix}{row_vals}")
    return "\n".join(lines)


def _encode_primitive(value: object, delimiter: str) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_number(value)
    if isinstance(value, str):
        return _encode_string(value, delimiter)
    raise ToonEncodeError(f"Cannot encode {type(value).__name__} as a TOON primitive")


def _format_number(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        return "null"
    if value == 0.0 and math.copysign(1.0, value) < 0:
        return "0"
    if value == int(value) and not math.isinf(value):
        return str(int(value))
    # Use repr for short, accurate representation, then normalize
    result = repr(value)
    if "e" in result or "E" in result:
        result = f"{value:.20f}"
        result = result.rstrip("0").rstrip(".")
    return result


def _encode_string(value: str, delimiter: str) -> str:
    if _needs_quoting(value, delimiter):
        return '"' + _escape(value) + '"'
    return value


def _needs_quoting(value: str, delimiter: str) -> bool:
    if not value:
        return True
    if value in _RESERVED:
        return True
    if _NUMERIC_RE.match(value) or _LEADING_ZERO_RE.match(value):
        return True
    if value.startswith(" ") or value.endswith(" "):
        return True
    if value == "-" or value.startswith("-"):
        return True
    structural = set(':"\\/[]{}')
    if any(c in structural for c in value):
        return True
    if "\n" in value or "\r" in value or "\t" in value:
        return True
    return delimiter in value


def _escape(value: str) -> str:
    result: list[str] = []
    for ch in value:
        if ch in _ESCAPE_MAP:
            result.append(_ESCAPE_MAP[ch])
        else:
            result.append(ch)
    return "".join(result)


def _encode_key(key: str) -> str:
    if _UNQUOTED_KEY_RE.match(key):
        return key
    return '"' + _escape(key) + '"'


def _is_all_primitives(arr: Sequence) -> bool:
    return all(not isinstance(item, (Mapping, Sequence)) or isinstance(item, (str, bytes)) for item in arr)


def _is_tabular(arr: Sequence) -> bool:
    if not arr:
        return False
    if not all(isinstance(item, Mapping) for item in arr):
        return False
    keys = set(arr[0].keys())
    if not keys:
        return False
    return all(
        set(item.keys()) == keys
        and all(not isinstance(v, (Mapping, Sequence)) or isinstance(v, (str, bytes)) for v in item.values())
        for item in arr
    )


def _delimiter_symbol(delimiter: str) -> str:
    if delimiter == ",":
        return ""
    if delimiter == "\t":
        return "\t"
    if delimiter == "|":
        return "|"
    return ""
