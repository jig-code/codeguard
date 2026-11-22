#!/bin/sh
# When an agent stops: lint, format, import boundaries and types. A failing check blocks
# the stop, and its output goes to the agent.
cd "$CLAUDE_PROJECT_DIR" || exit 0
command -v uv >/dev/null || exit 0
status=0
for check in "ruff check" "ruff format --check" "lint-imports" "basedpyright"; do
  if ! output=$(uv run --quiet --frozen $check 2>&1); then
    printf '`uv run %s` failed:\n%s\n\n' "$check" "$output" >&2
    status=2
  fi
done
exit $status
