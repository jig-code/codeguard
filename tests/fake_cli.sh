#!/bin/sh
exec "$(dirname "$0")/.fake-python" "$(dirname "$0")/.fake-cli" "$0" "$@"
