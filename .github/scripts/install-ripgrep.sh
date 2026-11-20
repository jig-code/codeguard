#!/bin/sh
# Install ripgrep, which the Gemini and Bedrock judges search files with, unless it's
# already on PATH. Usage:
#   .github/scripts/install-ripgrep.sh
set -eu
if command -v rg >/dev/null; then
  exit 0
fi
if command -v apt-get >/dev/null; then
  sudo apt-get update -q
  sudo apt-get install -y -q ripgrep
else
  brew install ripgrep
fi
