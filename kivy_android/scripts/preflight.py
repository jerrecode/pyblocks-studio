#!/usr/bin/env python3
from __future__ import annotations

import ast
import configparser
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pyblocks.catalog import Catalog
from pyblocks.codegen import PythonGenerator
from pyblocks.model import Workspace


REQUIRED = (
    "main.py",
    "buildozer.spec",
    "requirements.txt",
    "pyblocks/__init__.py",
    "pyblocks/model.py",
    "pyblocks/catalog.py",
    "pyblocks/codegen.py",
    "pyblocks/storage.py",
    "pyblocks/runtime.py",
    "pyblocks/app.py",
)


def validate_files() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"Missing required files: {', '.join(missing)}")


def validate_python() -> None:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
    if failures:
        raise RuntimeError("Python syntax failures:\n" + "\n".join(failures))


def validate_buildozer() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ROOT / "buildozer.spec", encoding="utf-8")
    app = parser["app"]
    if app.get("source.dir") != ".":
        raise RuntimeError("buildozer.spec must package this directory")
    requirements = {item.strip() for item in app.get("requirements", "").split(",")}
    if "python3" not in requirements:
        raise RuntimeError("python3 is missing from Buildozer requirements")
    if not any(item == "kivy" or item.startswith("kivy==") for item in requirements):
        raise RuntimeError("Kivy is missing from Buildozer requirements")
    if int(app.get("android.minapi", "0")) < 21:
        raise RuntimeError("android.minapi is unexpectedly old")
    if not app.get("android.archs", "").strip():
        raise RuntimeError("No Android architectures configured")


def validate_semantics() -> None:
    catalog = Catalog()
    workspace = Workspace(name="preflight")
    imported = workspace.add(catalog.get("import"))
    imported.fields["module"] = "math"
    function = workspace.add(catalog.get("function"))
    function.fields.update({"name": "square", "parameters": "value"})
    returned = workspace.add(catalog.get("return"))
    returned.fields["value"] = "value ** 2"
    printed = workspace.add(catalog.get("print"))
    printed.fields["value"] = "square(4)"
    workspace.connect_body(function.id, returned.id)
    workspace.connect_next(imported.id, function.id)
    workspace.connect_next(function.id, printed.id)
    generated = PythonGenerator(catalog).generate(workspace)
    compile(generated.source, "<preflight>", "exec")
    namespace = {"__name__": "__preflight__"}
    exec(compile(generated.source, "<preflight>", "exec"), namespace, namespace)
    restored = Workspace.from_dict(workspace.to_dict())
    if restored.to_dict() != workspace.to_dict():
        raise RuntimeError("Workspace serialization did not round-trip")


def main() -> int:
    validate_files()
    validate_python()
    validate_buildozer()
    validate_semantics()
    print("PyBlocks Studio Android preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
