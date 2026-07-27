from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .model import Workspace


class WorkspaceStore:
    """Atomic JSON persistence rooted in an app-owned writable directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.workspaces = self.root / "workspaces"
        self.exports = self.root / "exports"
        self.workspaces.mkdir(parents=True, exist_ok=True)
        self.exports.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_name(name: str) -> str:
        normalized = "".join(character if character.isalnum() or character in "-_" else "-" for character in name.strip())
        normalized = "-".join(part for part in normalized.split("-") if part)
        return normalized[:80] or "untitled"

    def workspace_path(self, name: str) -> Path:
        return self.workspaces / f"{self.safe_name(name)}.json"

    def save(self, workspace: Workspace) -> Path:
        path = self.workspace_path(workspace.name)
        self._atomic_json(path, workspace.to_dict())
        return path

    def load(self, name: str) -> Workspace:
        path = self.workspace_path(name)
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Workspace document must contain a JSON object")
        return Workspace.from_dict(value)

    def list_names(self) -> list[str]:
        return sorted(path.stem for path in self.workspaces.glob("*.json"))

    def delete(self, name: str) -> bool:
        path = self.workspace_path(name)
        if not path.exists():
            return False
        path.unlink()
        return True

    def export_python(self, workspace: Workspace, source: str) -> Path:
        path = self.exports / f"{self.safe_name(workspace.name)}.py"
        self._atomic_text(path, source)
        return path

    def export_descriptor(self, name: str, value: dict[str, Any]) -> Path:
        path = self.exports / f"{self.safe_name(name)}-block-specs.json"
        self._atomic_json(path, value)
        return path

    @staticmethod
    def _atomic_json(path: Path, value: Any) -> None:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        WorkspaceStore._atomic_text(path, text)

    @staticmethod
    def _atomic_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
