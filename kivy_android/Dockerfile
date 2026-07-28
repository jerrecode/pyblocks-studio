FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BUILDOZER_WARN_ON_ROOT=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf automake build-essential ccache cmake git \
    libffi-dev libltdl-dev libncurses5-dev libncursesw5-dev \
    libssl-dev libtool openjdk-17-jdk patch pkg-config \
    python3 python3-dev python3-pip python3-venv unzip zip zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN python3 -m venv /opt/buildenv \
    && /opt/buildenv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/buildenv/bin/pip install "buildozer>=1.5,<2" "cython<3"

ENV PATH="/opt/buildenv/bin:${PATH}"

CMD ["bash", "-lc", "python3 scripts/preflight.py && buildozer -v android debug"]
