# Build instructions

These commands do not depend on executable Git file modes.

## Validate

```bash
cd kivy_android
make preflight
make test
```

## Run on desktop

```bash
cd kivy_android
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
make desktop
```

## Build a debug APK on Debian/Ubuntu

```bash
cd kivy_android
make deps
make apk
```

Equivalent commands without `make`:

```bash
bash scripts/install-build-deps-debian.sh
bash scripts/build-android.sh debug
```

## Build in Docker

```bash
cd kivy_android
make docker-apk
```

The resulting files are placed in `kivy_android/bin/`.
