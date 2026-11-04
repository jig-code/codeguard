#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
# codeguard reviews and tests a git repository's working tree.
git init --quiet
git add --all
git -c user.name=eval -c user.email=eval@example.com commit --quiet --message "Start the case"
