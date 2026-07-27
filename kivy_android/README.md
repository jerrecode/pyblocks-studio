# PyBlocks Studio for Android

This directory contains the native Kivy implementation of PyBlocks Studio. It preserves the Python-oriented block graph and code-generation model while replacing the browser/React rendering layer with touch-native Kivy widgets suitable for Android packaging.

## Features

- Touch-first block palette and draggable workspace.
- Statement stacking and nested-body relationships.
- Editable block fields with live Python generation.
- Built-in Python syntax, functions, classes, exceptions, context managers, generators, and async blocks.
- Runtime discovery of members from importable Python modules.
- JSON workspace persistence in Kivy's app-private data directory.
- Python and descriptor artifact export.
- Captured stdout, stderr, and tracebacks for generated programs.
- Buildozer configuration for Android APK and AAB builds.

## Desktop development

```bash
cd kivy_android
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Validate without Kivy

```bash
cd kivy_android
python scripts/preflight.py
python -m unittest discover -s tests -v
```

## Build a debug APK on Debian/Ubuntu

```bash
cd kivy_android
./scripts/install-build-deps-debian.sh
./scripts/build-android.sh debug
```

The APK is written to `kivy_android/bin/`.

A clean Docker-based build is also available:

```bash
cd kivy_android
./scripts/build-android-docker.sh
```

## Android execution model

Generated Python executes inside the application's Python interpreter. It can import modules packaged into the APK through `buildozer.spec`. Android does not provide an unrestricted desktop Python environment, so packages requiring native libraries must be declared as python-for-android recipes or otherwise supported by the Android toolchain.

Workspace files, generated code, module descriptors, and runtime output are stored below `App.user_data_dir`; this avoids obsolete broad-storage permissions and works with Android scoped storage.
