from __future__ import annotations

import contextlib
import io
import threading
import time
import traceback
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    source: str
    stdout: str
    stderr: str
    traceback: str
    duration_seconds: float
    completed: bool
    timed_out: bool = False

    @property
    def successful(self) -> bool:
        return self.completed and not self.timed_out and not self.traceback


class PythonRuntime:
    """Executes generated code in an isolated namespace on a worker thread.

    CPython threads cannot be killed safely. The timeout therefore controls when
    the UI stops waiting; code that never returns may keep its daemon thread
    alive until the app process exits.
    """

    def execute(
        self,
        source: str,
        *,
        timeout: float = 8.0,
        globals_factory: Callable[[], dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        queue: Queue[ExecutionResult] = Queue(maxsize=1)

        def worker() -> None:
            started = time.monotonic()
            stdout = io.StringIO()
            stderr = io.StringIO()
            exception_text = ""
            namespace = {
                "__name__": "__pyblocks__",
                "__package__": None,
                "__builtins__": __builtins__,
            }
            if globals_factory:
                namespace.update(globals_factory())
            try:
                compiled = compile(source, "<pyblocks>", "exec")
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exec(compiled, namespace, namespace)
            except BaseException:
                exception_text = traceback.format_exc()
            duration = time.monotonic() - started
            queue.put(
                ExecutionResult(
                    source=source,
                    stdout=stdout.getvalue(),
                    stderr=stderr.getvalue(),
                    traceback=exception_text,
                    duration_seconds=duration,
                    completed=True,
                )
            )

        thread = threading.Thread(target=worker, name="pyblocks-runtime", daemon=True)
        thread.start()
        try:
            return queue.get(timeout=max(0.1, timeout))
        except Empty:
            return ExecutionResult(
                source=source,
                stdout="",
                stderr="",
                traceback="Execution exceeded the configured UI timeout.\n",
                duration_seconds=timeout,
                completed=False,
                timed_out=True,
            )

    def execute_async(
        self,
        source: str,
        callback: Callable[[ExecutionResult], None],
        *,
        timeout: float = 8.0,
    ) -> threading.Thread:
        def run() -> None:
            callback(self.execute(source, timeout=timeout))

        thread = threading.Thread(target=run, name="pyblocks-runtime-dispatch", daemon=True)
        thread.start()
        return thread
