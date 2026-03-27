"""PLOON schema: build schema declarations from data and parse them back into trees."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from tknpack.core.errors import PloonDecodeError, PloonEncodeError


@dataclass
class SchemaNode:
    name: str
    kind: str  # "field" | "object" | "array" | "primitive_array"
    children: list[SchemaNode] = field(default_factory=list)
    count: int = 0


def build_schema(data: dict | list, root_name: str = "") -> tuple[str, SchemaNode]:
    """Build a PLOON schema declaration string and tree from data.

    Returns (schema_string, schema_tree).
    """
    if isinstance(data, Mapping):
        # Single dict: check if it has exactly one key that maps to a list
        keys = list(data.keys())
        if len(keys) == 1 and isinstance(data[keys[0]], list):
            arr_key = keys[0]
            arr = data[arr_key]
            return _build_root_array_schema(arr_key, arr)
        # Flat dict or dict with multiple keys: treat as single-record object
        return _build_object_schema(data, root_name or "root")
    if isinstance(data, list):
        return _build_root_array_schema(root_name, data)
    raise PloonEncodeError(f"Cannot build schema for {type(data).__name__}")


def _build_root_array_schema(name: str, arr: list) -> tuple[str, SchemaNode]:
    if not arr:
        node = SchemaNode(name=name, kind="array", count=0)
        schema_str = f"[{name}#0]()" if name else "[#0]()"
        return schema_str, node

    first = arr[0]
    if not isinstance(first, Mapping):
        # Primitive array
        node = SchemaNode(name=name, kind="primitive_array", count=len(arr))
        schema_str = f"[{name}#{len(arr)}]()" if name else f"[#{len(arr)}]()"
        return schema_str, node

    # Array of objects — infer field schema from union of all keys
    all_keys = _collect_union_keys(arr)
    children = _infer_children(arr, all_keys)
    node = SchemaNode(name=name, kind="array", children=children, count=len(arr))
    fields_str = ",".join(_node_to_schema_field(c) for c in children)
    schema_str = f"[{name}#{len(arr)}]({fields_str})" if name else f"[#{len(arr)}]({fields_str})"
    return schema_str, node


def _build_object_schema(data: Mapping, name: str) -> tuple[str, SchemaNode]:
    children: list[SchemaNode] = []
    for key, value in data.items():
        children.append(_infer_field_node(key, value))
    node = SchemaNode(name=name, kind="object", children=children)
    fields_str = ",".join(_node_to_schema_field(c) for c in children)
    schema_str = f"[{name}#1]({fields_str})"
    return schema_str, node


def _collect_union_keys(arr: Sequence) -> list[str]:
    seen: dict[str, int] = {}
    for item in arr:
        if isinstance(item, Mapping):
            for key in item:
                if key not in seen:
                    seen[key] = len(seen)
    return sorted(seen, key=lambda k: seen[k])


def _infer_children(arr: Sequence, keys: list[str]) -> list[SchemaNode]:
    children: list[SchemaNode] = []
    for key in keys:
        # Find the first non-None value for this key to determine type
        sample = None
        for item in arr:
            if isinstance(item, Mapping) and key in item and item[key] is not None:
                sample = item[key]
                break
        children.append(_infer_field_node(key, sample))
    return children


def _infer_field_node(key: str, value: object) -> SchemaNode:
    if isinstance(value, Mapping):
        sub_children: list[SchemaNode] = []
        for k, v in value.items():
            sub_children.append(_infer_field_node(k, v))
        return SchemaNode(name=key, kind="object", children=sub_children)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if not value:
            return SchemaNode(name=key, kind="primitive_array", count=0)
        first = value[0]
        if isinstance(first, Mapping):
            all_keys = _collect_union_keys(value)
            sub_children = _infer_children(value, all_keys)
            return SchemaNode(name=key, kind="array", children=sub_children, count=len(value))
        return SchemaNode(name=key, kind="primitive_array", count=len(value))

    return SchemaNode(name=key, kind="field")


def _node_to_schema_field(node: SchemaNode) -> str:
    if node.kind == "field":
        return node.name
    if node.kind == "primitive_array":
        return f"{node.name}#()"
    if node.kind == "array":
        inner = ",".join(_node_to_schema_field(c) for c in node.children)
        return f"{node.name}#({inner})"
    if node.kind == "object":
        inner = ",".join(_node_to_schema_field(c) for c in node.children)
        return f"{node.name}{{{inner}}}"
    return node.name


# ---------------------------------------------------------------------------
# Schema parser: schema string → SchemaNode tree
# ---------------------------------------------------------------------------


def parse_schema(schema_line: str) -> tuple[str, int, SchemaNode]:
    """Parse a PLOON schema declaration.

    Returns (root_name, count, schema_tree).
    """
    schema_line = schema_line.strip()
    if not schema_line.startswith("["):
        raise PloonDecodeError(f"Invalid schema line: {schema_line}")

    # Extract root: [name#count](fields...)
    bracket_end = schema_line.index("]")
    bracket_content = schema_line[1:bracket_end]

    if "#" in bracket_content:
        parts = bracket_content.split("#", 1)
        root_name = parts[0]
        count = int(parts[1])
    else:
        root_name = bracket_content
        count = 0

    # Extract fields: (fields...)
    rest = schema_line[bracket_end + 1 :]
    if not rest.startswith("(") or not rest.endswith(")"):
        raise PloonDecodeError(f"Invalid schema fields: {rest}")

    fields_str = rest[1:-1]
    children = _parse_fields(fields_str) if fields_str else []

    if not children and count > 0:
        # Primitive array root
        node = SchemaNode(name=root_name, kind="primitive_array", count=count)
    else:
        node = SchemaNode(name=root_name, kind="array", children=children, count=count)

    return root_name, count, node


def _parse_fields(fields_str: str) -> list[SchemaNode]:
    """Parse comma-separated field declarations respecting nesting."""
    nodes: list[SchemaNode] = []
    depth = 0
    current: list[str] = []

    for ch in fields_str:
        if ch in ("(", "{"):
            depth += 1
            current.append(ch)
        elif ch in (")", "}"):
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            token = "".join(current).strip()
            if token:
                nodes.append(_parse_single_field(token))
            current = []
        else:
            current.append(ch)

    token = "".join(current).strip()
    if token:
        nodes.append(_parse_single_field(token))

    return nodes


def _parse_single_field(token: str) -> SchemaNode:
    """Parse a single field token like 'name', 'items#(id,name)', or 'addr{city,zip}'."""
    # Array field: name#(subfields) or name#()
    hash_idx = token.find("#")
    if hash_idx != -1:
        name = token[:hash_idx]
        rest = token[hash_idx + 1 :]
        if rest.startswith("(") and rest.endswith(")"):
            inner = rest[1:-1]
            if not inner:
                return SchemaNode(name=name, kind="primitive_array")
            children = _parse_fields(inner)
            return SchemaNode(name=name, kind="array", children=children)

    # Object field: name{subfields}
    brace_idx = token.find("{")
    if brace_idx != -1:
        name = token[:brace_idx]
        rest = token[brace_idx:]
        if rest.startswith("{") and rest.endswith("}"):
            inner = rest[1:-1]
            children = _parse_fields(inner)
            return SchemaNode(name=name, kind="object", children=children)

    # Plain field
    return SchemaNode(name=token, kind="field")
