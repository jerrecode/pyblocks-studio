[app]

title = PyBlocks Studio
package.name = pyblocksstudio
package.domain = org.jerrecode
source.dir = .
source.include_exts = py,kv,json,txt,md,ini,sh,yml,yaml
source.exclude_dirs = .git,.venv,venv,bin,.buildozer,__pycache__,tests
version = 0.1.0
requirements = python3,kivy==2.3.1
orientation = landscape
fullscreen = 0

# Android packaging
android.api = 35
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.enable_androidx = True
android.private_storage = True
android.logcat_filters = python:D *:S

# Keep the application offline-first and permission-minimal.
android.permissions =

[buildozer]
log_level = 2
warn_on_root = 1
