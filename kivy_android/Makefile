.PHONY: preflight test desktop deps apk release docker-apk clean

PYTHON ?= python3

preflight:
	$(PYTHON) scripts/preflight.py

test:
	$(PYTHON) -m unittest discover -s tests -v

desktop:
	$(PYTHON) main.py

deps:
	bash scripts/install-build-deps-debian.sh

apk: preflight
	bash scripts/build-android.sh debug

release: preflight
	bash scripts/build-android.sh release

docker-apk: preflight
	bash scripts/build-android-docker.sh

clean:
	rm -rf .buildozer bin .venv-build __pycache__ pyblocks/__pycache__ tests/__pycache__
