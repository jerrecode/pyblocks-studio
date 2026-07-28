[app]

title = PyBlocks Studio
package.name = pyblocksstudiopreview
package.domain = org.jerrecode
source.dir = .
source.include_exts = py,kv,json,txt,md,ini,sh,yml,yaml
source.exclude_dirs = .git,.venv,venv,bin,.buildozer,__pycache__,tests
version = 0.1.1
requirements = python3,kivy==2.3.1
orientation = landscape
fullscreen = 0

# Android packaging
android.api = 35
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.enable_androidx = True
android.private_storage = True
android.logcat_filters = python:D *:S

# No Android permissions are required. Do not add an empty android.permissions key:
# python-for-android turns that into the invalid-looking android.permission. entry.

[buildozer]
log_level = 2
warn_on_root = 1
