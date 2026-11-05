import os

import pytest
from packaging.version import Version
from pydantic import ValidationError

from codeguard.config import (
    BindingConfig,
    BindingsConfig,
    Config,
    GitPackageConfig,
    JudgeConfig,
    JudgeModel,
    JudgeProvider,
    PathPackageConfig,
    RuleOverride,
    RulesetConfig,
    Severity,
)


def messages(error: pytest.ExceptionInfo[ValidationError]) -> list[str]:
    return [problem["msg"] for problem in error.value.errors()]


def write_skill(tmp_path, name: str = "placement"):
    (tmp_path / name).mkdir()
    (tmp_path / name / "SKILL.md").write_text("# Placement\n")
    return tmp_path / name


class TestBindingsConfig:
    def test_relative_skill_is_under_the_working_tree(self, tmp_path):
        skill = write_skill(tmp_path)

        bindings = BindingsConfig.model_validate(
            {"placement.yaml": {"skill": "placement", "paths": ["**"], "triggers": ["any"]}},
            context={"working_tree": tmp_path},
        )

        assert bindings.root["placement.yaml"].skill == skill

    def test_skill_without_skill_file_is_an_error(self, tmp_path):
        (tmp_path / "placement").mkdir()

        with pytest.raises(ValidationError) as error:
            BindingsConfig.model_validate(
                {"placement.yaml": {"skill": "placement", "paths": ["**"], "triggers": ["any"]}},
                context={"working_tree": tmp_path},
            )

        assert messages(error) == [f"Value error, {tmp_path}/placement has no SKILL.md"]

    def test_retired_disable_skips_is_ignored(self, tmp_path):
        skill = write_skill(tmp_path)

        bindings = BindingsConfig.model_validate(
            {
                "placement.yaml": {
                    "skill": skill,
                    "paths": ["**"],
                    "triggers": ["any"],
                    "disable_skips": ["renames"],
                }
            }
        )

        assert bindings.root["placement.yaml"] == BindingConfig(
            triggers=frozenset({"any"}), skill=skill, paths=("**",)
        )

    def test_skill_bound_twice_is_an_error(self, tmp_path):
        skill = write_skill(tmp_path)
        binding = {"skill": skill, "paths": ["**"], "triggers": ["any"]}

        with pytest.raises(ValidationError) as error:
            BindingsConfig.model_validate({"a.yaml": binding, "b.yaml": binding})

        assert messages(error) == [
            f"Value error, skill {skill} is bound more than once: a.yaml, b.yaml"
        ]


class TestPackagesConfig:
    def test_git_package_has_its_url_and_ref(self):
        config = Config.model_validate(
            {
                "packages": [
                    {
                        "kind": "git",
                        "git": "https://example.com/rules.git",
                        "ref": "v1.0.0",
                        "rulesets": {"python": {}},
                    }
                ]
            }
        )

        assert config.packages == (
            GitPackageConfig(
                git="https://example.com/rules.git",
                ref="v1.0.0",
                rulesets={"python": RulesetConfig()},
            ),
        )

    def test_path_package_is_under_the_working_tree(self, tmp_path):
        (tmp_path / "rules").mkdir()

        config = Config.model_validate(
            {"packages": [{"kind": "path", "path": "rules", "rulesets": {"python": {}}}]},
            context={"working_tree": tmp_path},
        )

        assert config.packages == (
            PathPackageConfig(path=tmp_path / "rules", rulesets={"python": RulesetConfig()}),
        )

    def test_package_without_rulesets_is_an_error(self):
        with pytest.raises(ValidationError):
            Config.model_validate(
                {
                    "packages": [
                        {
                            "kind": "git",
                            "git": "https://example.com/rules.git",
                            "ref": "v1.0.0",
                            "rulesets": {},
                        }
                    ]
                }
            )

    def test_versioned_package_is_an_error(self):
        with pytest.raises(ValidationError):
            Config.model_validate(
                {
                    "packages": [
                        {
                            "kind": "versioned",
                            "git": "https://example.com/rules.git",
                            "version": ">=0.2,<1",
                            "rulesets": {"python": {}},
                        }
                    ]
                }
            )

    def test_git_package_without_ref_is_an_error(self):
        with pytest.raises(ValidationError):
            Config.model_validate(
                {
                    "packages": [
                        {
                            "kind": "git",
                            "git": "https://example.com/rules.git",
                            "rulesets": {"python": {}},
                        }
                    ]
                }
            )

    def test_package_without_a_kind_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            Config.model_validate(
                {
                    "packages": [
                        {
                            "git": "https://example.com/rules.git",
                            "ref": "v1.0.0",
                            "rulesets": {"python": {}},
                        }
                    ]
                }
            )

        assert messages(error) == ["Unable to extract tag using discriminator 'kind'"]


class TestAstGrepConfig:
    def test_ast_grep_is_the_project_version(self):
        config = Config.model_validate({"ast-grep": "0.45.3"})

        assert config == Config(ast_grep=Version("0.45.3"))

    def test_ast_grep_range_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            Config.model_validate({"ast-grep": ">=0.45"})

        assert messages(error) == ["Value error, Invalid version: '>=0.45'"]


class TestRulesetConfig:
    def test_rule_both_excluded_and_overridden_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            RulesetConfig.model_validate(
                {"exclude": ["no-print"], "rules": {"no-print": {"severity": "warning"}}}
            )

        assert messages(error) == ["Value error, excluded rules are also overridden: no-print"]

    def test_include_with_exclude_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            RulesetConfig.model_validate({"include": ["no-print"], "exclude": ["no-breakpoint"]})

        assert messages(error) == ["Value error, set include or exclude, not both"]

    def test_override_replaces_only_the_fields_it_sets(self, tmp_path):
        skill = write_skill(tmp_path)
        bindings = BindingsConfig.model_validate(
            {
                "placement.yaml": {
                    "skill": skill,
                    "paths": ["**"],
                    "triggers": ["any"],
                    "model": "claude-haiku-5-5",
                }
            }
        )
        selection = RulesetConfig(rules={"placement": RuleOverride(severity=Severity.WARNING)})

        binding = selection.apply("placement", bindings.root["placement.yaml"])

        assert binding == BindingConfig(
            triggers=frozenset({"any"}),
            skill=skill,
            paths=("**",),
            severity=Severity.WARNING,
            model="claude-haiku-5-5",
        )

    def test_ruleset_severity_applies_to_a_rule_without_an_override(self, tmp_path):
        skill = write_skill(tmp_path)
        bindings = BindingsConfig.model_validate(
            {"placement.yaml": {"skill": skill, "paths": ["**"], "triggers": ["any"]}}
        )

        binding = RulesetConfig(severity=Severity.WARNING).apply(
            "placement", bindings.root["placement.yaml"]
        )

        assert binding == BindingConfig(
            triggers=frozenset({"any"}), skill=skill, paths=("**",), severity=Severity.WARNING
        )

    def test_rule_override_severity_wins_over_the_ruleset_severity(self, tmp_path):
        skill = write_skill(tmp_path)
        bindings = BindingsConfig.model_validate(
            {
                "placement.yaml": {
                    "skill": skill,
                    "paths": ["**"],
                    "triggers": ["any"],
                    "severity": "info",
                }
            }
        )
        selection = RulesetConfig(
            severity=Severity.WARNING, rules={"placement": RuleOverride(severity=Severity.ERROR)}
        )

        binding = selection.apply("placement", bindings.root["placement.yaml"])

        assert binding == BindingConfig(
            triggers=frozenset({"any"}), skill=skill, paths=("**",), severity=Severity.ERROR
        )

    def test_rule_override_without_severity_takes_the_ruleset_severity(self, tmp_path):
        skill = write_skill(tmp_path)
        bindings = BindingsConfig.model_validate(
            {"placement.yaml": {"skill": skill, "paths": ["**"], "triggers": ["any"]}}
        )
        selection = RulesetConfig(
            severity=Severity.WARNING, rules={"placement": RuleOverride(paths=("app/**",))}
        )

        binding = selection.apply("placement", bindings.root["placement.yaml"])

        assert binding == BindingConfig(
            triggers=frozenset({"any"}), skill=skill, paths=("app/**",), severity=Severity.WARNING
        )

    def test_rule_runs_outside_ci_by_default(self):
        assert not RulesetConfig().is_ci_only("placement")

    def test_ruleset_ci_only_applies_to_a_rule_without_an_override(self):
        assert RulesetConfig(ci_only=True).is_ci_only("placement")

    def test_rule_ci_only_wins_over_the_ruleset_ci_only(self):
        selection = RulesetConfig(ci_only=True, rules={"placement": RuleOverride(ci_only=False)})

        assert not selection.is_ci_only("placement")

    def test_rule_override_model_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            RuleOverride.model_validate({"model": "claude-haiku-5-5"})

        assert messages(error) == [
            "Value error, model: a rule is judged with the model its binding names"
        ]

    @pytest.mark.parametrize("provider", ["gemini", "bedrock"])
    def test_api_binding_without_a_model_is_an_error(self, tmp_path, provider):
        skill = write_skill(tmp_path)

        with pytest.raises(ValidationError) as error:
            BindingConfig.model_validate({"skill": skill, "paths": ["**"], "provider": provider})

        assert messages(error) == [f"Value error, provider {provider} needs a model"]

    def test_codex_binding_uses_its_selected_model(self, tmp_path):
        skill = write_skill(tmp_path)

        binding = BindingConfig.model_validate(
            {
                "skill": skill,
                "paths": ["**/*.py"],
                "provider": "codex-cli",
                "model": "a-bound-model",
            }
        )

        assert binding.judge_model == JudgeModel(
            provider=JudgeProvider.CODEX_CLI, name="a-bound-model"
        )


class TestJudgeConfig:
    def test_claude_runs_a_call_per_cpu_at_once(self):
        assert JudgeConfig().concurrency(JudgeProvider.CLAUDE_CLI) == os.process_cpu_count()

    def test_gemini_runs_two_calls_at_once(self):
        assert JudgeConfig().concurrency(JudgeProvider.GEMINI) == 2

    def test_calls_at_once_sets_the_concurrency(self):
        assert JudgeConfig(calls_at_once=1).concurrency(JudgeProvider.GEMINI) == 1


def test_codex_concurrency_uses_the_cli_limit():
    assert JudgeConfig().concurrency(JudgeProvider.CODEX_CLI) == os.process_cpu_count()


def test_codex_default_remains_luna():
    assert JudgeProvider.CODEX_CLI.default_model == "gpt-6-luna"
