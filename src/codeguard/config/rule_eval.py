from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from codeguard.config.config_error import ConfigError
from codeguard.config.languages import language_of
from codeguard.config.ruleset import JUDGE_EVAL_DIR
from codeguard.line_range import LineRange

_EVAL_FILE_SUFFIXES = (".yaml", ".yml")


class Outcome(StrEnum):
    INVALID = "invalid"
    VALID = "valid"
    SKIPPED = "skipped"


class FileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str = "module.py"
    before: str | None = None
    after: str
    unchanged: dict[str, str] = {}

    @model_validator(mode="after")
    def paths_are_inside_the_repository(self) -> Self:
        for path in (self.file, *self.unchanged):
            posix = PurePosixPath(path)
            if posix.is_absolute() or ".." in posix.parts or str(posix) != path or not posix.parts:
                raise ValueError(f"{path} is not a normalized relative path")
            if ".git" in posix.parts:
                raise ValueError(f"{path} is inside .git")
        return self

    @model_validator(mode="after")
    def file_is_not_unchanged(self) -> Self:
        if self.file in self.unchanged:
            raise ValueError(f"unchanged lists the edited file {self.file}")
        return self

    def before_files(self, prefix: str = "") -> dict[str, str]:
        unchanged = {f"{prefix}{path}": text for path, text in self.unchanged.items()}
        if self.before is None:
            return unchanged
        return {**unchanged, f"{prefix}{self.file}": self.before}

    def after_files(self, prefix: str = "") -> dict[str, str]:
        unchanged = {f"{prefix}{path}": text for path, text in self.unchanged.items()}
        return {**unchanged, f"{prefix}{self.file}": self.after}


class JudgedViolation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lines: LineRange
    message: str
    kinds: tuple[str, ...] | None = None


class EditVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: Outcome
    # The judge's reason for its verdict; a skipped edit has none.
    reason: str | None = None
    violations: tuple[JudgedViolation, ...] = ()

    @property
    def listing(self) -> str:
        reason = "" if self.reason is None else f"\n  reason: {self.reason}"
        return reason + "".join(
            f"\n  {violation.lines.described}: {violation.message}" for violation in self.violations
        )


class RuleEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    inputs: FileEdit
    expected_output: EditVerdict

    @field_validator("expected_output")
    @classmethod
    def expects_no_reason(cls, expected: EditVerdict) -> EditVerdict:
        if expected.reason is not None:
            raise ValueError(
                "a case expects no reason: the judge's reason is printed with the eval for "
                "whoever reads it, never checked"
            )
        return expected


class RuleEval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    cases: tuple[RuleEvalCase, ...]

    def by_language(self, languages: frozenset[str]) -> tuple[tuple[str | None, Self], ...]:
        """Split the eval by the language of each case's file, for a rule whose paths name
        several languages, so each language is evaluated and reported as `<rule> (<language>)`.
        A rule that names one language or none keeps one eval, for its language if any."""
        if len(languages) < 2:
            return ((next(iter(languages), None), self),)
        cases: dict[str | None, list[RuleEvalCase]] = {}
        for case in self.cases:
            language = language_of(case.inputs.file)
            cases.setdefault(language if language in languages else None, []).append(case)
        return tuple(
            (
                language,
                self.model_copy(
                    update={
                        "name": self.name if language is None else f"{self.name} ({language})",
                        "cases": tuple(grouped),
                    }
                ),
            )
            for language, grouped in sorted(cases.items(), key=lambda item: item[0] or "")
        )

    @field_validator("cases")
    @classmethod
    def names_are_unique(cls, cases: tuple[RuleEvalCase, ...]) -> tuple[RuleEvalCase, ...]:
        names = [case.name for case in cases]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError(f"cases share a name: {', '.join(repeated)}")
        return cases


@dataclass(frozen=True)
class RuleEvalReader:
    ruleset: Path

    def read(self) -> list[tuple[Path, RuleEval]]:
        directory = self.ruleset / JUDGE_EVAL_DIR
        files = sorted(file for file in directory.glob("*") if file.suffix in _EVAL_FILE_SUFFIXES)
        evals = [self._read_file(file) for file in files]
        names = [rule_eval.name for _, rule_eval in evals]
        doubled = [file for file, rule_eval in evals if names.count(rule_eval.name) > 1]
        if doubled:
            raise ConfigError(
                "a rule has one eval file; remove one of:"
                + "".join(f"\n  {file}" for file in doubled)
            )
        return evals

    @staticmethod
    def _read_file(file: Path) -> tuple[Path, RuleEval]:
        try:
            data = yaml.safe_load(file.read_text())
        except yaml.YAMLError as error:
            raise ConfigError(f"{file} is invalid:\n  {error}") from error
        if isinstance(data, dict) and "id" in data:
            raise ConfigError(
                f"{file} is a codeguard 0.4 rule eval; convert it to rule-evals/<rule id>.yaml"
            )
        if isinstance(data, dict):
            data = {"name": file.stem, **data}
        try:
            return file, RuleEval.model_validate(data)
        except ValidationError as error:
            raise ConfigError.invalid(file, error) from error
