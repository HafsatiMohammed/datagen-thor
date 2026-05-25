#!/usr/bin/env bash
set -euo pipefail

if ! command -v curl >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y curl
fi

curl -fsSL https://ollama.com/install.sh | sh

sudo systemctl enable ollama || true
sudo systemctl start ollama || true

ollama -v
