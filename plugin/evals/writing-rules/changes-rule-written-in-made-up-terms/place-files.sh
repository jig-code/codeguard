#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
# A fixture file that breaks a rule on purpose is named <name>.invalid.<ext> in the
# repository; the run sees it under its real name.
find . -path ./.git -prune -o -name '*.invalid.*' -type f -print | while read -r f; do
  mv "$f" "${f/.invalid./.}"
done
# codeguard reviews and tests a git repository's working tree.
git init --quiet
git add --all
git -c user.name=eval -c user.email=eval@example.com commit --quiet --message "Start the case"
