from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from .model import BlockKind, BlockSpec, FieldSpec


CATEGORY_COLORS = {
    "Control": "#d97706",
    "Functions": "#7c3aed",
    "Classes": "#9333ea",
    "Data": "#2563eb",
    "Operators": "#0891b2",
    "Text": "#0f766e",
    "Collections": "#047857",
    "Modules": "#4f46e5",
    "Exceptions": "#dc2626",
    "Async": "#c026d3",
    "Context": "#b45309",
    "Runtime": "#475569",
}


def field(name: str, default: str = "", type_name: str = "str", placeholder: str = "") -> FieldSpec:
    return FieldSpec(name=name, default=default, type_name=type_name, placeholder=placeholder)


def block(
    block_id: str,
    label: str,
    category: str,
    template: str,
    *fields: FieldSpec,
    has_body: bool = False,
    kind: BlockKind = BlockKind.STATEMENT,
    description: str = "",
) -> BlockSpec:
    return BlockSpec(
        id=block_id,
        label=label,
        category=category,
        color=CATEGORY_COLORS.get(category, "#4f46e5"),
        template=template,
        fields=tuple(fields),
        has_body=has_body,
        kind=kind,
        description=description,
    )


CORE_SPECS: tuple[BlockSpec, ...] = (
    block("import", "import module", "Modules", "import {module}", field("module", "math")),
    block(
        "from_import",
        "from module import name",
        "Modules",
        "from {module} import {name}",
        field("module", "pathlib"),
        field("name", "Path"),
    ),
    block("assign", "set variable", "Data", "{target} = {value}", field("target", "value"), field("value", "0", "expression")),
    block("aug_assign", "update variable", "Data", "{target} {operator}= {value}", field("target", "value"), field("operator", "+"), field("value", "1", "expression")),
    block("expression", "expression", "Operators", "{expression}", field("expression", "1 + 1", "expression")),
    block("print", "print", "Runtime", "print({value})", field("value", "'Hello from PyBlocks'", "expression")),
    block("return", "return", "Functions", "return {value}", field("value", "None", "expression")),
    block("yield", "yield", "Functions", "yield {value}", field("value", "None", "expression")),
    block("raise", "raise", "Exceptions", "raise {exception}", field("exception", "ValueError('message')", "expression")),
    block("assert", "assert", "Exceptions", "assert {condition}, {message}", field("condition", "True", "expression"), field("message", "'assertion failed'", "expression")),
    block("pass", "pass", "Control", "pass"),
    block("break", "break", "Control", "break"),
    block("continue", "continue", "Control", "continue"),
    block("if", "if", "Control", "if {condition}:", field("condition", "True", "expression"), has_body=True),
    block("elif", "elif", "Control", "elif {condition}:", field("condition", "False", "expression"), has_body=True),
    block("else", "else", "Control", "else:", has_body=True),
    block("while", "while", "Control", "while {condition}:", field("condition", "True", "expression"), has_body=True),
    block("for", "for item in iterable", "Control", "for {target} in {iterable}:", field("target", "item"), field("iterable", "range(3)", "expression"), has_body=True),
    block("match", "match", "Control", "match {subject}:", field("subject", "value", "expression"), has_body=True),
    block("case", "case", "Control", "case {pattern}:", field("pattern", "_"), has_body=True),
    block("function", "define function", "Functions", "def {name}({parameters}):", field("name", "my_function"), field("parameters", ""), has_body=True, kind=BlockKind.HAT),
    block("async_function", "define async function", "Async", "async def {name}({parameters}):", field("name", "main"), field("parameters", ""), has_body=True, kind=BlockKind.HAT),
    block("class", "define class", "Classes", "class {name}({bases}):", field("name", "MyClass"), field("bases", "object"), has_body=True, kind=BlockKind.HAT),
    block("try", "try", "Exceptions", "try:", has_body=True),
    block("except", "except", "Exceptions", "except {exception} as {name}:", field("exception", "Exception"), field("name", "error"), has_body=True),
    block("finally", "finally", "Exceptions", "finally:", has_body=True),
    block("with", "with context manager", "Context", "with {expression} as {target}:", field("expression", "open('file.txt')", "expression"), field("target", "handle"), has_body=True),
    block("async_with", "async with", "Async", "async with {expression} as {target}:", field("expression", "manager", "expression"), field("target", "resource"), has_body=True),
    block("async_for", "async for", "Async", "async for {target} in {iterable}:", field("target", "item"), field("iterable", "stream", "expression"), has_body=True),
    block("await", "await", "Async", "await {expression}", field("expression", "task()", "expression")),
    block("call", "call function", "Functions", "{callable}({arguments})", field("callable", "function"), field("arguments", "")),
    block("list_append", "append to list", "Collections", "{target}.append({value})", field("target", "items"), field("value", "value", "expression")),
    block("dict_set", "set dictionary item", "Collections", "{target}[{key}] = {value}", field("target", "mapping"), field("key", "'key'", "expression"), field("value", "value", "expression")),
    block("comment", "comment", "Text", "# {text}", field("text", "comment")),
    block("raw", "raw Python", "Runtime", "{code}", field("code", "pass"), description="Insert a complete Python statement."),
)


class Catalog:
    def __init__(self, specs: Iterable[BlockSpec] = CORE_SPECS) -> None:
        self._specs: dict[str, BlockSpec] = {item.id: item for item in specs}

    def __iter__(self):
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)

    def get(self, spec_id: str) -> BlockSpec:
        try:
            return self._specs[spec_id]
        except KeyError as exc:
            raise KeyError(f"Unknown block specification: {spec_id}") from exc

    def add(self, spec: BlockSpec, *, replace: bool = False) -> None:
        if spec.id in self._specs and not replace:
            raise ValueError(f"Block specification already exists: {spec.id}")
        self._specs[spec.id] = spec

    def categories(self) -> list[str]:
        return sorted({item.category for item in self._specs.values()})

    def search(self, query: str = "", category: str | None = None) -> list[BlockSpec]:
        needle = query.strip().casefold()
        result = []
        for spec in self._specs.values():
            if category and category != "All" and spec.category != category:
                continue
            haystack = f"{spec.label} {spec.id} {spec.description} {spec.template}".casefold()
            if needle and needle not in haystack:
                continue
            result.append(spec)
        return sorted(result, key=lambda item: (item.category, item.label))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "blocks": [
                {
                    **asdict(item),
                    "kind": item.kind.value,
                    "fields": [asdict(field_spec) for field_spec in item.fields],
                }
                for item in self._specs.values()
            ],
        }

    def export_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def discover_module(self, module_name: str, *, max_members: int = 150) -> list[BlockSpec]:
        module_name = module_name.strip()
        if not module_name:
            raise ValueError("A module name is required")
        module = importlib.import_module(module_name)
        discovered: list[BlockSpec] = []
        for name, value in inspect.getmembers(module):
            if name.startswith("_"):
                continue
            if len(discovered) >= max_members:
                break
            full_name = f"{module_name}.{name}"
            safe_id = "module:" + full_name
            if inspect.isclass(value):
                signature = _safe_signature(value)
                discovered.append(
                    block(
                        safe_id,
                        f"construct {full_name}",
                        "Modules",
                        "{target} = " + full_name + "({arguments})",
                        field("target", name[:1].lower() + name[1:]),
                        field("arguments", _signature_defaults(signature)),
                        description=_safe_doc(value),
                    )
                )
            elif callable(value):
                signature = _safe_signature(value)
                discovered.append(
                    block(
                        safe_id,
                        f"call {full_name}",
                        "Modules",
                        full_name + "({arguments})",
                        field("arguments", _signature_defaults(signature)),
                        description=_safe_doc(value),
                    )
                )
            else:
                discovered.append(
                    block(
                        safe_id,
                        f"read {full_name}",
                        "Modules",
                        "{target} = " + full_name,
                        field("target", name.lower()),
                        description=f"Module attribute of type {type(value).__name__}",
                    )
                )
        for spec in discovered:
            self.add(spec, replace=True)
        return discovered

    @staticmethod
    def available_top_level_modules(limit: int = 300) -> list[str]:
        names = sorted({item.name for item in pkgutil.iter_modules()})
        return names[:limit]


def _safe_signature(value: Any) -> inspect.Signature | None:
    try:
        return inspect.signature(value)
    except (TypeError, ValueError):
        return None


def _signature_defaults(signature: inspect.Signature | None) -> str:
    if signature is None:
        return ""
    arguments: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.name in {"self", "cls"}:
            continue
        if parameter.kind is parameter.VAR_POSITIONAL:
            arguments.append("*args")
        elif parameter.kind is parameter.VAR_KEYWORD:
            arguments.append("**kwargs")
        elif parameter.default is inspect.Parameter.empty:
            arguments.append(parameter.name)
        else:
            arguments.append(f"{parameter.name}={parameter.default!r}")
    return ", ".join(arguments)


def _safe_doc(value: Any, limit: int = 220) -> str:
    text = inspect.getdoc(value) or ""
    return " ".join(text.split())[:limit]
