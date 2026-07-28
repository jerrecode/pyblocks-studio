#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y \
  autoconf \
  automake \
  build-essential \
  ccache \
  cmake \
  git \
  libffi-dev \
  libltdl-dev \
  libncurses5-dev \
  libncursesw5-dev \
  libssl-dev \
  libtool \
  openjdk-17-jdk \
  patch \
  pkg-config \
  python3 \
  python3-dev \
  python3-pip \
  python3-venv \
  unzip \
  zip \
  zlib1g-dev

python3 -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install "buildozer>=1.5,<2" "cython<3"

echo "Build dependencies installed in $(pwd)/.venv-build"
