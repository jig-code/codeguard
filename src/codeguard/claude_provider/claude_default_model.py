import json
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import logfire

_EXECUTABLE = "claude"
_MODEL_VARIABLE = "ANTHROPIC_MODEL"
# Admin-managed settings, which apply over every other, on Linux and on macOS.
_MANAGED_SETTINGS = (
    Path("/etc/claude-code/managed-settings.json"),
    Path("/Library/Application Support/ClaudeCode/managed-settings.json"),
)
# An alias such as `opus` or `sonnet[1m]` names the latest model of a family, which changes
# with the CLI, so it doesn't say which model judges.
_ALIAS = re.compile(r"[a-z]+(\[\w+\])?")
_PROBE_SECONDS = 60


@dataclass(frozen=True)
class ClaudeDefaultModel:
    """The model the `claude` CLI runs when it's given no --model: the one its environment
    or settings name, read where the CLI reads them, else the one a small call reports."""

    root: Path
    executable: str = _EXECUTABLE
    environment: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    home: Path = field(default_factory=Path.home)
    managed_settings: tuple[Path, ...] = _MANAGED_SETTINGS

    def resolve(self, probe: bool = True) -> str | None:
        """The model, or None when it can't be told: with `probe` off, before asking the
        CLI; with it on, when the call fails."""
        return self.configured() or (self.probed() if probe else None)

    def configured(self) -> str | None:
        """The model the environment or settings name by id, in the CLI's precedence: the
        environment over settings, and a settings file's `env` over any file's `model`."""
        settings = [self._settings(file) for file in self._settings_files()]
        named = [
            self.environment.get(_MODEL_VARIABLE),
            *(_env_model(file) for file in settings),
            *(file.get("model") for file in settings),
        ]
        model = next((model for model in named if isinstance(model, str) and model), None)
        return None if model is None or _ALIAS.fullmatch(model) else model

    def probed(self) -> str | None:
        """The model a minimal call to the CLI reports it ran, or None when the call fails."""
        with logfire.span("claude reports its default model") as span:
            try:
                process = subprocess.run(
                    [
                        self.executable,
                        "--safe-mode",
                        "-p",
                        "--output-format",
                        "stream-json",
                        "--verbose",
                        "--tools",
                        "",
                        "--permission-prompts",
                        "none",
                        "--system-prompt",
                        "Reply with OK.",
                        "--no-session-persistence",
                    ],
                    input="OK?",
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=_PROBE_SECONDS,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                return None
            model = _reported_model(process.stdout) if process.returncode == 0 else None
            span.set_attribute("model", model)
            return model

    def _settings_files(self) -> list[Path]:
        user = Path(self.environment.get("CLAUDE_CONFIG_DIR") or self.home / ".claude")
        return [
            *self.managed_settings,
            self.root / ".claude" / "settings.local.json",
            self.root / ".claude" / "settings.json",
            user / "settings.json",
        ]

    def _settings(self, file: Path) -> dict[str, object]:
        try:
            settings = json.loads(file.read_text())
        except (OSError, ValueError):
            return {}
        return settings if isinstance(settings, dict) else {}


def _env_model(settings: Mapping[str, object]) -> object:
    env = settings.get("env")
    return env.get(_MODEL_VARIABLE) if isinstance(env, dict) else None


def _reported_model(stream: str) -> str | None:
    """The model the stream's init message names, else the one its result's usage names."""
    usage: list[str] = []
    for line in stream.splitlines():
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict):
            continue
        if message.get("type") == "system" and isinstance(message.get("model"), str):
            return message["model"]
        if message.get("type") == "result" and isinstance(message.get("modelUsage"), dict):
            usage = sorted(message["modelUsage"])
    return ",".join(usage) or None
