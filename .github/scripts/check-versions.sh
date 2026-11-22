#!/bin/sh
# Check that both plugin manifests and the release the plugin's launcher runs give the
# same version, the plugin's. pyproject.toml's version may run ahead of it between
# releases. With an argument, a release's version, also check that the plugin's version
# and pyproject.toml's are that one. Usage:
#   .github/scripts/check-versions.sh [version]
set -eu

launcher=plugin/bin/codeguard
plugin_version="$(sed -n 's/^version=//p' "$launcher")"
status=0

for manifest in plugin/.claude-plugin/plugin.json plugin/.codex-plugin/plugin.json; do
  manifest_version="$(jq -r .version "$manifest")"
  if [ "$manifest_version" != "$plugin_version" ]; then
    echo "::error file=$manifest::version is $manifest_version, but $launcher runs $plugin_version"
    status=1
  fi
done

if [ "$#" -gt 0 ]; then
  project_version="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
  if [ "$project_version" != "$1" ]; then
    echo "::error file=pyproject.toml::version is $project_version, but the tag is v$1"
    status=1
  fi
  if [ "$plugin_version" != "$1" ]; then
    echo "::error file=$launcher::version is $plugin_version, but the tag is v$1"
    status=1
  fi
fi

exit "$status"
