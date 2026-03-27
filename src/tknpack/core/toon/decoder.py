"""TOON v3.0 decoder: TOON string → Python objects."""

from __future__ import annotations

import re
from typing import Any

from tknpack.core.errors import ToonDecodeError

_ROOT_ARRAY_HEADER_RE = re.compile(
    r"^(\[(\d+)([\t|])?\])"
    r"(\{([^}]*)\})?"
    r":\s*(.*)"
)

_ARRAY_HEADER_RE = re.compile(
    r"^(\[(\d+)([\t|])?\])"
    r"(\{([^}]*)\})?"
    r":$"
)

_KEY_ARRAY_RE = re.compile(
    r'^("(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z0-9_.]*)'
    r"\[(\d+)([\t|])?\]"
    r"(\{([^}]*)\})?"
    r":\s*(.*)"
)

_KEY_VALUE_RE = re.compile(r'^("(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z0-9_.]*)\s*:\s?(.*)')
_QUOTED_KEY_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"')

_UNESCAPE_MAP = {
    "\\\\": "\\",
    '\\"': '"',
    "\\n": "\n",
    "\\r": "\r",
    "\\t": "\t",
}


def toon_decode(text: str) -> dict | list | str | int | float | bool | None:
    if not text.strip():
        return {}

    lines = text.split("\n")

    first_content = _first_nonempty(lines)
    if first_content is None:
        return {}

    first_stripped = first_content.strip()

    # Root array: starts with [N]
    if _ROOT_ARRAY_HEADER_RE.match(first_stripped):
        return _parse_root_array(lines)

    # Object field with array header: key[N]: ... or key[N]{fields}:
    if _KEY_ARRAY_RE.match(first_stripped):
        return _parse_object(lines, 0, 0, len(lines))

    # Regular key-value: key: value
    if _KEY_VALUE_RE.match(first_stripped):
        return _parse_object(lines, 0, 0, len(lines))

    # Single primitive value
    nonempty = [line for line in lines if line.strip()]
    if len(nonempty) == 1:
        return _parse_primitive_value(nonempty[0].strip(), ",")

    return _parse_object(lines, 0, 0, len(lines))


def _indent_level(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _first_nonempty(lines: list[str]) -> str | None:
    for line in lines:
        if line.strip():
            return line
    return None


def _detect_indent_size(lines: list[str], start: int, end: int, base_indent: int) -> int:
    for i in range(start, end):
        line = lines[i]
        if not line.strip():
            continue
        indent = _indent_level(line)
        if indent > base_indent:
            return indent - base_indent
    return 2


def _parse_root_array(lines: list[str]) -> list[Any]:
    first = lines[0].strip()
    m = _ROOT_ARRAY_HEADER_RE.match(first)
    if not m:
        raise ToonDecodeError(f"Invalid root array header: {first}")

    count = int(m.group(2))
    delim_char = m.group(3) or ","
    fields_str = m.group(5)
    inline_part = m.group(6).strip() if m.group(6) else ""

    if count == 0:
        return []

    if fields_str is not None:
        field_names = _split_fields(fields_str, delim_char)
        rows = [line for line in lines[1:] if line.strip()]
        result: list[Any] = []
        for row_line in rows[:count]:
            vals = _split_row(row_line.strip(), delim_char)
            obj: dict[str, Any] = {}
            for j, fname in enumerate(field_names):
                obj[fname] = _parse_primitive_value(vals[j] if j < len(vals) else "", delim_char)
            result.append(obj)
        return result

    if inline_part and not fields_str:
        vals = _split_row(inline_part, delim_char)
        return [_parse_primitive_value(v, delim_char) for v in vals]

    return _parse_list_items(lines, 1, len(lines), _detect_indent_size(lines, 1, len(lines), 0), 0)


def _parse_object(lines: list[str], base_indent: int, start: int, end: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    i = start
    while i < end:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        indent = _indent_level(line)
        if indent < base_indent:
            break
        if indent > base_indent:
            i += 1
            continue

        content = line.strip()

        ka = _KEY_ARRAY_RE.match(content)
        if ka:
            key = _unquote_key(ka.group(1))
            count = int(ka.group(2))
            delim_char = ka.group(3) or ","
            fields_str = ka.group(5)
            inline = ka.group(6).strip() if ka.group(6) else ""

            if count == 0:
                result[key] = []
                i += 1
                continue

            if fields_str is not None:
                field_names = _split_fields(fields_str, delim_char)
                child_indent = base_indent + _detect_indent_size(lines, i + 1, end, base_indent)
                rows: list[Any] = []
                j = i + 1
                while j < end and len(rows) < count:
                    rl = lines[j]
                    if not rl.strip():
                        j += 1
                        continue
                    ri = _indent_level(rl)
                    if ri < child_indent:
                        break
                    vals = _split_row(rl.strip(), delim_char)
                    obj: dict[str, Any] = {}
                    for k_idx, fname in enumerate(field_names):
                        obj[fname] = _parse_primitive_value(vals[k_idx] if k_idx < len(vals) else "", delim_char)
                    rows.append(obj)
                    j += 1
                result[key] = rows
                i = j
                continue
            elif inline:
                vals = _split_row(inline, delim_char)
                result[key] = [_parse_primitive_value(v, delim_char) for v in vals]
                i += 1
                continue
            else:
                child_indent = base_indent + _detect_indent_size(lines, i + 1, end, base_indent)
                block_end = _find_block_end(lines, i + 1, end, child_indent)
                result[key] = _parse_list_items(lines, i + 1, block_end, child_indent, base_indent)
                i = block_end
                continue

        kv = _KEY_VALUE_RE.match(content)
        if kv:
            raw_key = kv.group(1)
            key = _unquote_key(raw_key)
            value_str = kv.group(2).strip()

            if not value_str:
                child_indent = base_indent + _detect_indent_size(lines, i + 1, end, base_indent)
                block_end = _find_block_end(lines, i + 1, end, child_indent)
                if block_end > i + 1:
                    first_child = _first_nonempty(lines[i + 1 : block_end])
                    if first_child and first_child.strip().startswith("- "):
                        result[key] = _parse_list_items(lines, i + 1, block_end, child_indent, base_indent)
                    else:
                        result[key] = _parse_object(lines, child_indent, i + 1, block_end)
                else:
                    result[key] = {}
                i = block_end
            else:
                result[key] = _parse_primitive_value(value_str, ",")
                i += 1
        else:
            i += 1

    return result


def _parse_list_items(lines: list[str], start: int, end: int, item_indent: int, parent_indent: int) -> list[Any]:
    result: list[Any] = []
    i = start
    while i < end:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        indent = _indent_level(line)
        if indent < item_indent:
            break
        content = line[item_indent:]

        if content.startswith("- "):
            item_content = content[2:]

            arr_key, arr_match = _try_parse_array_header_with_key(item_content)
            if arr_key is not None and arr_match is not None:
                m = arr_match
                key = _unquote_key(arr_key)
                count = int(m.group(2))
                delim_char = m.group(3) or ","
                fields_str = m.group(5)

                colon_idx = item_content.index(":")
                inline = item_content[colon_idx + 1 :].strip()

                if fields_str is not None:
                    field_names = _split_fields(fields_str, delim_char)
                    rows: list[Any] = []
                    j = i + 1
                    row_indent = item_indent + _detect_indent_size(lines, i + 1, end, item_indent)
                    while j < end and len(rows) < count:
                        rl = lines[j]
                        if not rl.strip():
                            j += 1
                            continue
                        ri = _indent_level(rl)
                        if ri < row_indent:
                            break
                        vals = _split_row(rl.strip(), delim_char)
                        obj: dict[str, Any] = {}
                        for k_idx, fn in enumerate(field_names):
                            obj[fn] = _parse_primitive_value(vals[k_idx] if k_idx < len(vals) else "", delim_char)
                        rows.append(obj)
                        j += 1
                    item_obj: dict[str, Any] = {key: rows}
                    cont_indent = item_indent + 2
                    while j < end:
                        cl = lines[j]
                        if not cl.strip():
                            j += 1
                            continue
                        ci = _indent_level(cl)
                        if ci < cont_indent:
                            break
                        cc = cl.strip()
                        ckv = _KEY_VALUE_RE.match(cc)
                        if ckv:
                            ck = _unquote_key(ckv.group(1))
                            cv = ckv.group(2).strip()
                            item_obj[ck] = _parse_primitive_value(cv, ",") if cv else {}
                        j += 1
                    result.append(item_obj)
                    i = j
                    continue
                elif inline:
                    vals = _split_row(inline, delim_char)
                    inner = [_parse_primitive_value(v, delim_char) for v in vals]
                    item_obj = {key: inner}
                    result.append(item_obj)
                    i += 1
                    continue

            kv = _KEY_VALUE_RE.match(item_content)
            if kv:
                raw_key = kv.group(1)
                key = _unquote_key(raw_key)
                value_str = kv.group(2).strip()

                obj = {}
                if value_str:
                    obj[key] = _parse_primitive_value(value_str, ",")
                else:
                    obj[key] = {}

                cont_indent = item_indent + 2
                j = i + 1
                while j < end:
                    cl = lines[j]
                    if not cl.strip():
                        j += 1
                        continue
                    ci = _indent_level(cl)
                    if ci < cont_indent:
                        break
                    cc = cl.strip()
                    ckv = _KEY_VALUE_RE.match(cc)
                    if ckv:
                        ck = _unquote_key(ckv.group(1))
                        cv = ckv.group(2).strip()
                        if cv:
                            obj[ck] = _parse_primitive_value(cv, ",")
                        else:
                            nested_indent = ci + _detect_indent_size(lines, j + 1, end, ci)
                            nested_end = _find_block_end(lines, j + 1, end, nested_indent)
                            obj[ck] = _parse_object(lines, nested_indent, j + 1, nested_end)
                            j = nested_end
                            continue
                    j += 1
                result.append(obj)
                i = j
                continue

            inner_arr_match = re.match(r"\[(\d+)([\t|])?\]:\s*(.*)", item_content)
            if inner_arr_match:
                count = int(inner_arr_match.group(1))
                delim_c = inner_arr_match.group(2) or ","
                inline = inner_arr_match.group(3).strip()
                if inline:
                    vals = _split_row(inline, delim_c)
                    result.append([_parse_primitive_value(v, delim_c) for v in vals])
                else:
                    result.append([])
                i += 1
                continue

            result.append(_parse_primitive_value(item_content.strip(), ","))
            i += 1
            continue

        elif content.startswith("-"):
            if content == "-":
                result.append({})
                i += 1
                continue

        i += 1

    return result


def _try_parse_array_header_with_key(content: str) -> tuple[str | None, re.Match | None]:
    key_match = _QUOTED_KEY_RE.match(content)
    if key_match:
        raw_key = key_match.group(0)
        rest = content[len(raw_key) :]
    else:
        m2 = re.match(r"([A-Za-z_][A-Za-z0-9_.]*)", content)
        if m2:
            raw_key = m2.group(1)
            rest = content[len(raw_key) :]
        else:
            return None, None

    arr_m = _ARRAY_HEADER_RE.match(rest)
    if arr_m:
        return raw_key, arr_m
    return None, None


def _find_block_end(lines: list[str], start: int, end: int, child_indent: int) -> int:
    for i in range(start, end):
        line = lines[i]
        if not line.strip():
            continue
        if _indent_level(line) < child_indent:
            return i
    return end


def _split_fields(fields_str: str, delimiter: str) -> list[str]:
    delim = delimiter if delimiter != "," else ","
    parts = fields_str.split(delim)
    return [_unquote_key(p.strip()) for p in parts]


def _split_row(row: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_quotes = False
    i = 0
    while i < len(row):
        ch = row[i]
        if ch == '"' and not in_quotes:
            in_quotes = True
            current.append(ch)
        elif ch == '"' and in_quotes:
            current.append(ch)
            in_quotes = False
        elif ch == "\\" and in_quotes and i + 1 < len(row):
            current.append(ch)
            current.append(row[i + 1])
            i += 1
        elif ch == delimiter and not in_quotes:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current).strip())
    return parts


def _parse_primitive_value(value: str, delimiter: str) -> str | int | float | bool | None:
    if not value:
        return ""
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False

    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return _unescape(value[1:-1])

    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        pass

    return value


def _unescape(value: str) -> str:
    result: list[str] = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            two = value[i : i + 2]
            if two in _UNESCAPE_MAP:
                result.append(_UNESCAPE_MAP[two])
                i += 2
                continue
            else:
                raise ToonDecodeError(f"Invalid escape sequence: {two}")
        result.append(value[i])
        i += 1
    return "".join(result)


def _unquote_key(raw: str) -> str:
    if raw.startswith('"') and raw.endswith('"'):
        return _unescape(raw[1:-1])
    return raw
