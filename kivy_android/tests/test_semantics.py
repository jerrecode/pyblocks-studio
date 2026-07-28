from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pyblocks.catalog import Catalog
from pyblocks.codegen import CodeGenerationError, PythonGenerator
from pyblocks.model import Workspace
from pyblocks.runtime import PythonRuntime
from pyblocks.storage import WorkspaceStore


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = Catalog()

    def test_statement_stack_and_body_generate_valid_python(self) -> None:
        workspace = Workspace(name="example")
        function = workspace.add(self.catalog.get("function"))
        function.fields.update({"name": "double", "parameters": "value"})
        returned = workspace.add(self.catalog.get("return"))
        returned.fields["value"] = "value * 2"
        printed = workspace.add(self.catalog.get("print"))
        printed.fields["value"] = "double(4)"
        workspace.connect_body(function.id, returned.id)
        workspace.connect_next(function.id, printed.id)

        program = PythonGenerator(self.catalog).generate(workspace)
        self.assertIn("def double(value):", program.source)
        self.assertIn("    return value * 2", program.source)
        self.assertIn("print(double(4))", program.source)
        compile(program.source, "<test>", "exec")

    def test_cycle_is_rejected(self) -> None:
        workspace = Workspace()
        first = workspace.add(self.catalog.get("pass"))
        second = workspace.add(self.catalog.get("pass"))
        workspace.connect_next(first.id, second.id)
        with self.assertRaises(ValueError):
            workspace.connect_next(second.id, first.id)

    def test_serialization_round_trip(self) -> None:
        workspace = Workspace(name="round-trip")
        node = workspace.add(self.catalog.get("assign"), x=12, y=34)
        node.fields.update({"target": "answer", "value": "42"})
        restored = Workspace.from_dict(json.loads(json.dumps(workspace.to_dict())))
        self.assertEqual(workspace.to_dict(), restored.to_dict())

    def test_missing_body_gets_pass(self) -> None:
        workspace = Workspace()
        condition = workspace.add(self.catalog.get("if"))
        condition.fields["condition"] = "True"
        source = PythonGenerator(self.catalog).generate(workspace).source
        self.assertEqual(source, "if True:\n    pass\n")


class StorageAndRuntimeTests(unittest.TestCase):
    def test_atomic_store(self) -> None:
        catalog = Catalog()
        workspace = Workspace(name="stored")
        workspace.add(catalog.get("pass"))
        with tempfile.TemporaryDirectory() as directory:
            store = WorkspaceStore(directory)
            path = store.save(workspace)
            self.assertTrue(path.is_file())
            self.assertEqual(store.load("stored").to_dict(), workspace.to_dict())

    def test_runtime_captures_output_and_traceback(self) -> None:
        runtime = PythonRuntime()
        success = runtime.execute("print('ok')\n")
        self.assertTrue(success.successful)
        self.assertEqual(success.stdout, "ok\n")
        failure = runtime.execute("raise ValueError('bad')\n")
        self.assertFalse(failure.successful)
        self.assertIn("ValueError: bad", failure.traceback)


class CatalogTests(unittest.TestCase):
    def test_standard_library_discovery(self) -> None:
        catalog = Catalog()
        found = catalog.discover_module("math", max_members=20)
        self.assertTrue(found)
        self.assertTrue(any(item.id.startswith("module:math.") for item in found))
        self.assertTrue(catalog.search("math", "Modules"))


if __name__ == "__main__":
    unittest.main()
