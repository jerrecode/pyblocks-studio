# Android application

The native Kivy Android application is maintained in [`kivy_android/`](kivy_android/README.md).

Quick validation and build:

```bash
cd kivy_android
python3 scripts/preflight.py
./scripts/install-build-deps-debian.sh
./scripts/build-android.sh debug
```

A GitHub Actions workflow at `.github/workflows/kivy-android-apk.yml` validates the semantic model and builds a downloadable debug APK whenever the Android application changes on `main`.
