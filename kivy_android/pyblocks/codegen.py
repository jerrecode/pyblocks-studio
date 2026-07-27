from __future__ import annotations

import ast
from dataclasses import dataclass

from .catalog import Catalog
from .model import BlockNode, Workspace


class CodeGenerationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class GeneratedProgram:
    source: str
    line_to_node: dict[int, str]

    def compile(self, filename: str = "<pyblocks>") -> object:
        return compile(self.source, filename, "exec")


class PythonGenerator:
    def __init__(self, catalog: Catalog, *, indent: str = "    ") -> None:
        self.catalog = catalog
        self.indent = indent
        self._lines: list[str] = []
        self._line_to_node: dict[int, str] = {}

    def generate(self, workspace: Workspace) -> GeneratedProgram:
        workspace.validate()
        self._lines = []
        self._line_to_node = {}
        for index, root_id in enumerate(workspace.ordered_roots()):
            self._emit_chain(workspace, root_id, 0)
            if index < len(workspace.roots) - 1 and self._lines and self._lines[-1] != "":
                self._lines.append("")
        source = "\n".join(self._lines).rstrip() + "\n"
        try:
            ast.parse(source, filename="<pyblocks>", mode="exec")
        except SyntaxError as exc:
            raise CodeGenerationError(
                f"Generated Python is invalid at line {exc.lineno}: {exc.msg}"
            ) from exc
        return GeneratedProgram(source=source, line_to_node=dict(self._line_to_node))

    def _emit_chain(self, workspace: Workspace, node_id: str, depth: int) -> None:
        seen: set[str] = set()
        current_id: str | None = node_id
        while current_id:
            if current_id in seen:
                raise CodeGenerationError(f"Cycle in statement stack at {current_id}")
            seen.add(current_id)
            current = workspace.nodes[current_id]
            self._emit_node(workspace, current, depth)
            current_id = current.next_id

    def _emit_node(self, workspace: Workspace, node: BlockNode, depth: int) -> None:
        spec = self.catalog.get(node.spec_id)
        values = {item.name: node.fields.get(item.name, item.default) for item in spec.fields}
        try:
            rendered = spec.template.format_map(_SafeFormat(values))
        except (KeyError, ValueError) as exc:
            raise CodeGenerationError(f"Could not render block {spec.label}: {exc}") from exc
        rendered_lines = rendered.splitlines() or ["pass"]
        for rendered_line in rendered_lines:
            self._append(self.indent * depth + rendered_line, node.id)
        if spec.has_body:
            if node.body_ids:
                for child_id in node.body_ids:
                    self._emit_chain(workspace, child_id, depth + 1)
            else:
                self._append(self.indent * (depth + 1) + "pass", node.id)

    def _append(self, line: str, node_id: str) -> None:
        self._lines.append(line)
        self._line_to_node[len(self._lines)] = node_id


class _SafeFormat(dict[str, str]):
    def __missing__(self, key: str) -> str:
        raise KeyError(f"Missing block field {key!r}")
