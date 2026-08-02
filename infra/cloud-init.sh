#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  age \
  build-essential \
  ca-certificates \
  curl \
  git \
  gh \
  jq \
  nftables \
  nodejs \
  npm \
  pipx \
  python3 \
  python3-venv \
  rsync \
  tmux \
  unzip \
  yq

install -d -m 0755 /opt/general-ai-agent

apt-get clean
rm -rf /var/lib/apt/lists/*
