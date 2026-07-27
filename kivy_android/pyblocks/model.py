from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Iterable
from uuid import uuid4


class BlockKind(StrEnum):
    STATEMENT = "statement"
    EXPRESSION = "expression"
    HAT = "hat"


class ConnectorKind(StrEnum):
    PREVIOUS = "previous"
    NEXT = "next"
    BODY = "body"
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    default: str = ""
    type_name: str = "str"
    placeholder: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FieldSpec":
        return cls(
            name=str(value["name"]),
            default=str(value.get("default", "")),
            type_name=str(value.get("type_name", "str")),
            placeholder=str(value.get("placeholder", "")),
        )


@dataclass(frozen=True, slots=True)
class BlockSpec:
    id: str
    label: str
    category: str
    kind: BlockKind = BlockKind.STATEMENT
    color: str = "#4f46e5"
    template: str = "pass"
    fields: tuple[FieldSpec, ...] = ()
    has_body: bool = False
    description: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BlockSpec":
        return cls(
            id=str(value["id"]),
            label=str(value["label"]),
            category=str(value.get("category", "Other")),
            kind=BlockKind(value.get("kind", BlockKind.STATEMENT)),
            color=str(value.get("color", "#4f46e5")),
            template=str(value.get("template", "pass")),
            fields=tuple(FieldSpec.from_dict(item) for item in value.get("fields", [])),
            has_body=bool(value.get("has_body", False)),
            description=str(value.get("description", "")),
        )


@dataclass(slots=True)
class BlockNode:
    spec_id: str
    id: str = field(default_factory=lambda: uuid4().hex)
    x: float = 0.0
    y: float = 0.0
    fields: dict[str, str] = field(default_factory=dict)
    next_id: str | None = None
    body_ids: list[str] = field(default_factory=list)
    parent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BlockNode":
        return cls(
            spec_id=str(value["spec_id"]),
            id=str(value.get("id") or uuid4().hex),
            x=float(value.get("x", 0.0)),
            y=float(value.get("y", 0.0)),
            fields={str(k): str(v) for k, v in value.get("fields", {}).items()},
            next_id=value.get("next_id"),
            body_ids=[str(item) for item in value.get("body_ids", [])],
            parent_id=value.get("parent_id"),
        )


@dataclass(slots=True)
class Workspace:
    name: str = "Untitled"
    nodes: dict[str, BlockNode] = field(default_factory=dict)
    roots: list[str] = field(default_factory=list)
    schema_version: int = 1

    def add(self, spec: BlockSpec, *, x: float = 40.0, y: float = 40.0) -> BlockNode:
        values = {item.name: item.default for item in spec.fields}
        node = BlockNode(spec_id=spec.id, x=x, y=y, fields=values)
        self.nodes[node.id] = node
        self.roots.append(node.id)
        self.validate()
        return node

    def remove(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        descendants = list(self.walk_descendants(node_id))
        to_remove = {node_id, *descendants}
        for node in self.nodes.values():
            if node.next_id in to_remove:
                node.next_id = None
            node.body_ids = [item for item in node.body_ids if item not in to_remove]
        self.roots = [item for item in self.roots if item not in to_remove]
        for item in to_remove:
            self.nodes.pop(item, None)
        self.validate()

    def walk_descendants(self, node_id: str) -> Iterable[str]:
        node = self.nodes[node_id]
        if node.next_id and node.next_id in self.nodes:
            yield node.next_id
            yield from self.walk_descendants(node.next_id)
        for child_id in node.body_ids:
            if child_id in self.nodes:
                yield child_id
                yield from self.walk_descendants(child_id)

    def detach(self, node_id: str) -> None:
        node = self.nodes[node_id]
        for candidate in self.nodes.values():
            if candidate.next_id == node_id:
                candidate.next_id = None
            if node_id in candidate.body_ids:
                candidate.body_ids.remove(node_id)
        if node_id not in self.roots:
            self.roots.append(node_id)
        node.parent_id = None

    def connect_next(self, parent_id: str, child_id: str) -> None:
        self._check_pair(parent_id, child_id)
        if self._contains(child_id, parent_id):
            raise ValueError("A stack connection cannot create a cycle")
        self.detach(child_id)
        parent = self.nodes[parent_id]
        old_next = parent.next_id
        parent.next_id = child_id
        self.nodes[child_id].parent_id = parent_id
        self.roots = [item for item in self.roots if item != child_id]
        if old_next and old_next != child_id:
            tail = self.stack_tail(child_id)
            self.nodes[tail].next_id = old_next
            self.nodes[old_next].parent_id = tail
        self.validate()

    def connect_body(self, parent_id: str, child_id: str, *, index: int | None = None) -> None:
        self._check_pair(parent_id, child_id)
        if self._contains(child_id, parent_id):
            raise ValueError("A body connection cannot create a cycle")
        self.detach(child_id)
        parent = self.nodes[parent_id]
        if index is None:
            parent.body_ids.append(child_id)
        else:
            parent.body_ids.insert(max(0, index), child_id)
        self.nodes[child_id].parent_id = parent_id
        self.roots = [item for item in self.roots if item != child_id]
        self.validate()

    def stack_tail(self, node_id: str) -> str:
        current = node_id
        seen: set[str] = set()
        while self.nodes[current].next_id:
            if current in seen:
                raise ValueError("Cycle detected")
            seen.add(current)
            current = self.nodes[current].next_id or current
        return current

    def _check_pair(self, parent_id: str, child_id: str) -> None:
        if parent_id == child_id:
            raise ValueError("A node cannot connect to itself")
        if parent_id not in self.nodes or child_id not in self.nodes:
            raise KeyError("Unknown workspace node")

    def _contains(self, start_id: str, sought_id: str) -> bool:
        return start_id == sought_id or sought_id in set(self.walk_descendants(start_id))

    def ordered_roots(self) -> list[str]:
        return sorted(
            (item for item in self.roots if item in self.nodes),
            key=lambda item: (-self.nodes[item].y, self.nodes[item].x, item),
        )

    def validate(self) -> None:
        known = set(self.nodes)
        self.roots = list(dict.fromkeys(item for item in self.roots if item in known))
        references: dict[str, int] = {item: 0 for item in known}
        for node in self.nodes.values():
            if node.next_id:
                if node.next_id not in known:
                    raise ValueError(f"Unknown next node: {node.next_id}")
                references[node.next_id] += 1
            for child_id in node.body_ids:
                if child_id not in known:
                    raise ValueError(f"Unknown body node: {child_id}")
                references[child_id] += 1
        duplicates = [item for item, count in references.items() if count > 1]
        if duplicates:
            raise ValueError(f"Nodes have multiple structural parents: {duplicates}")
        for node_id, node in self.nodes.items():
            if references[node_id] == 0:
                node.parent_id = None
                if node_id not in self.roots:
                    self.roots.append(node_id)
            elif node_id in self.roots:
                self.roots.remove(node_id)
        for root_id in self.roots:
            if root_id in set(self.walk_descendants(root_id)):
                raise ValueError("Workspace contains a cycle")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "roots": list(self.roots),
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Workspace":
        workspace = cls(
            name=str(value.get("name", "Untitled")),
            schema_version=int(value.get("schema_version", 1)),
            nodes={
                str(node_id): BlockNode.from_dict(node)
                for node_id, node in value.get("nodes", {}).items()
            },
            roots=[str(item) for item in value.get("roots", [])],
        )
        workspace.validate()
        return workspace
