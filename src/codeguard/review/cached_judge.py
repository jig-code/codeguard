import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import logfire
from diskcache import Cache

from codeguard.review.judge import (
    INSTRUCTIONS,
    Judge,
    Judgement,
    JudgeRequest,
    Verdict,
    output_schema,
)

# The schema the providers send, so a change to what the model is told, a `Confidence`
# description included, judges every cached verdict again.
_CACHE_VERSION = "\0".join((INSTRUCTIONS, json.dumps(output_schema(Verdict))))


@dataclass(frozen=True)
class _StoredJudgement:
    verdict: Verdict
    loaded_digests: Mapping[str, str | None]

    def changed_files(self, digest_of: Callable[[str], str | None]) -> tuple[str, ...]:
        return tuple(
            file
            for file, digest in self.loaded_digests.items()
            if digest is None or digest_of(file) != digest
        )


@dataclass(frozen=True)
class CachedJudge:
    wrapped: Judge
    store: Cache
    root: Path
    version: str = _CACHE_VERSION

    @property
    def identity(self) -> str:
        return self.wrapped.identity

    def judge(self, request: JudgeRequest) -> Judgement:
        with logfire.span(
            "judge {rule} on {file}", rule=request.skill.name, file=request.file
        ) as span:
            key = self._key(request)
            stored = self._entry(key)
            changed = stored.changed_files(self._digest_of) if stored else ()
            span.set_attribute("cache_hit", stored is not None and not changed)
            span.set_attribute("changed_files", list(changed))
            if stored is None or changed:
                judgement = self.wrapped.judge(request)
                stored = _StoredJudgement(
                    judgement.verdict,
                    {file: self._digest_of(file) for file in judgement.loaded_files},
                )
                self.store[key] = stored
            span.set_attribute("loaded_files", list(stored.loaded_digests))
            span.set_attribute("violations", len(stored.verdict.violations))
            return Judgement(stored.verdict, tuple(stored.loaded_digests))

    def has(self, request: JudgeRequest) -> bool:
        stored = self._entry(self._key(request))
        return stored is not None and not stored.changed_files(self._digest_of)

    def _entry(self, key: str) -> _StoredJudgement | None:
        if key not in self.store:
            return None
        stored = self.store[key]
        if not isinstance(stored, _StoredJudgement):
            raise TypeError(f"cache entry {key} is not a stored judgement")
        return stored

    def _digest_of(self, file: str) -> str | None:
        root = self.root.resolve()
        path = (root / file).resolve()
        if not path.is_relative_to(root):
            return None
        return _digest(path.read_bytes()) if path.is_file() else "missing"

    def _key(self, request: JudgeRequest) -> str:
        parts = (
            self.version,
            self.identity,
            request.skill.text,
            request.file,
            _digest(request.changes.encode()),
            self._digest_of(request.file) or "",
        )
        return _digest("\0".join(parts).encode())


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
