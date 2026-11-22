#!/bin/sh
# Check that pyproject.toml, both plugin manifests and the release the plugin's launcher
# runs give the same version. With an argument, also check that the version is that one.
# Usage:
#   .github/scripts/check-versions.sh [version]
set -eu

version="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
status=0

for manifest in plugin/.claude-plugin/plugin.json plugin/.codex-plugin/plugin.json; do
  manifest_version="$(jq -r .version "$manifest")"
  if [ "$manifest_version" != "$version" ]; then
    echo "::error file=$manifest::version is $manifest_version, but pyproject.toml's is $version"
    status=1
  fi
done

launcher=plugin/bin/codeguard
launcher_version="$(sed -n 's/^version=//p' "$launcher")"
if [ "$launcher_version" != "$version" ]; then
  echo "::error file=$launcher::version is $launcher_version, but pyproject.toml's is $version"
  status=1
fi

if [ "$#" -gt 0 ] && [ "$1" != "$version" ]; then
  echo "::error file=pyproject.toml::version is $version, but the tag is v$1"
  status=1
fi

exit "$status"
