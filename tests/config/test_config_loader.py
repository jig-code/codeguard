import os
import traceback
from dataclasses import replace
from pathlib import Path
from unittest import mock

import pytest
from pydantic import SecretStr

from codeguard.config import (
    BindingConfig,
    BindingsConfig,
    ChangeKind,
    Config,
    ConfigError,
    ConfigLoader,
    GeminiSettings,
    JudgeConfig,
    JudgeProvider,
    PathPackageConfig,
    PatternBindingConfig,
    PatternBindingsConfig,
    Ruleset,
    RulesetConfig,
    RulesetLoader,
    Severity,
)

CONFIG = ".codeguard/config.yaml"
BINDING = ".codeguard/bindings/placement.yaml"
SKILL = ".claude/skills/responsibility-placement/SKILL.md"
ENUM_VALUE_GATE = "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n"
NO_PRINT_RULE = "id: no-print\nlanguage: python\nrule:\n  pattern: print($$$)\n"


class TestConfigLoader:
    def test_project_without_config_has_the_defaults(self, repo):
        config = ConfigLoader(repo.root).load()

        assert config == Config()

    def test_confidence_threshold_defaults_to_0_9(self, repo):
        assert ConfigLoader(repo.root).load().confidence_threshold == 0.9

    def test_loads_the_confidence_threshold(self, repo):
        repo.write(CONFIG, "confidence_threshold: 0.75\n")

        assert ConfigLoader(repo.root).load().confidence_threshold == 0.75

    def test_confidence_threshold_above_1_is_an_error(self, repo):
        repo.write(CONFIG, "confidence_threshold: 1.5\n")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  confidence_threshold: Input should be less than or equal to 1"
        )

    def test_review_time_limit_defaults_to_5_minutes(self, repo):
        assert ConfigLoader(repo.root).load().review_time_limit_minutes == 5

    def test_loads_the_review_time_limit(self, repo):
        repo.write(CONFIG, "review_time_limit_minutes: 10\n")

        assert ConfigLoader(repo.root).load().review_time_limit_minutes == 10

    def test_env_var_names_the_config_file_to_load(self, repo, monkeypatch):
        repo.write(CONFIG, "review_time_limit_minutes: 10\n")
        repo.write("codeguard.local.yaml", "review_time_limit_minutes: 20\n")
        monkeypatch.setenv("CODEGUARD_CONFIG", "codeguard.local.yaml")

        assert ConfigLoader(repo.root).load().review_time_limit_minutes == 20

    @mock.patch.dict(
        os.environ,
        {
            "CODEGUARD_JUDGE__GEMINI__PROJECT": "my-project",
            "CODEGUARD_JUDGE__GEMINI__LOCATION": "us",
            "CODEGUARD_JUDGE__GEMINI__API_KEY": "proxy-injected",
        },
    )
    def test_gemini_settings_come_from_the_environment(self, repo):
        assert ConfigLoader(repo.root).load().judge == JudgeConfig(
            gemini=GeminiSettings(
                project="my-project", location="us", api_key=SecretStr("proxy-injected")
            )
        )

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__GEMINI__API_KYE": "secret-key-value"})
    def test_mistyped_gemini_variable_is_an_error_that_leaves_out_its_value(self, repo):
        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        report = "".join(traceback.format_exception(error.value))
        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  judge.gemini.api_kye: Extra inputs are not permitted"
        )
        assert "secret-key-value" not in report

    def test_gemini_settings_in_the_config_file_are_an_error(self, repo):
        repo.write(CONFIG, "judge:\n  gemini:\n    project: my-project\n")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  judge.gemini: read from the environment only, not the config file"
        )

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__GEMINI__LOCATION": "us"})
    def test_gemini_settings_in_the_config_file_are_an_error_beside_gemini_variables(self, repo):
        repo.write(CONFIG, "judge:\n  gemini:\n    project: my-project\n")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  judge.gemini: read from the environment only, not the config file"
        )

    @mock.patch.dict(
        os.environ,
        {
            "CODEGUARD_JUDGE__GEMINI__API_KEY": "proxy-injected",
            "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE": "keys/judge.json",
        },
    )
    def test_gemini_api_key_and_credentials_file_together_are_an_error(self, repo):
        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  judge.gemini: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
            "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE, not both"
        )

    def test_loads_the_project_judge_default(self, repo):
        repo.write(CONFIG, "judge:\n  provider: bedrock\n  model: project-model\n")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(
            provider=JudgeProvider.BEDROCK, model="project-model"
        )

    def test_judge_env_vars_override_the_file(self, repo, monkeypatch):
        repo.write(CONFIG, "judge:\n  provider: codex-cli\n  model: file-model\n")
        monkeypatch.setenv("CODEGUARD_JUDGE__PROVIDER", "bedrock")
        monkeypatch.setenv("CODEGUARD_JUDGE__MODEL", "env-model")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(
            provider=JudgeProvider.BEDROCK, model="env-model"
        )

    def test_judge_env_var_keeps_the_file_other_judge_settings(self, repo, monkeypatch):
        repo.write(CONFIG, "judge:\n  calls_at_once: 1\n  model: file-model\n")
        monkeypatch.setenv("CODEGUARD_JUDGE__MODEL", "env-model")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(
            calls_at_once=1, model="env-model"
        )

    def test_judge_env_var_applies_without_a_config_file(self, repo, monkeypatch):
        monkeypatch.setenv("CODEGUARD_JUDGE__PROVIDER", "bedrock")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(provider=JudgeProvider.BEDROCK)

    def test_env_var_for_another_setting_is_ignored(self, repo, monkeypatch):
        repo.write(CONFIG, "confidence_threshold: 0.75\n")
        monkeypatch.setenv("CODEGUARD_CONFIDENCE_THRESHOLD", "0.8")

        assert ConfigLoader(repo.root).load().confidence_threshold == 0.75

    def test_env_var_for_another_judge_setting_is_ignored(self, repo, monkeypatch):
        repo.write(CONFIG, "judge:\n  calls_at_once: 1\n")
        monkeypatch.setenv("CODEGUARD_JUDGE__CALLS_AT_ONCE", "9")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(calls_at_once=1)

    def test_empty_judge_env_var_leaves_the_file_value(self, repo, monkeypatch):
        repo.write(CONFIG, "judge:\n  model: file-model\n")
        monkeypatch.setenv("CODEGUARD_JUDGE__MODEL", "")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(model="file-model")

    def test_unknown_judge_provider_in_the_environment_is_an_error(self, repo, monkeypatch):
        monkeypatch.setenv("CODEGUARD_JUDGE__PROVIDER", "openai")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value).startswith(
            f"{repo.root}/.codeguard is invalid:\n  judge.provider: Input should be "
        )

    def test_loads_a_path_package(self, repo):
        repo.write("rules/codeguard-package.yaml", "name: example\nrulesets: [python]\n")
        repo.write(
            CONFIG,
            "packages:\n"
            "  - kind: path\n"
            "    path: rules\n"
            "    rulesets:\n"
            "      python:\n"
            "        exclude: [no-print]\n",
        )

        config = ConfigLoader(repo.root).load()

        assert config.packages == (
            PathPackageConfig(
                path=Path("rules"),
                rulesets={"python": RulesetConfig(exclude=("no-print",))},
            ),
        )

    def test_empty_config_file_is_an_error(self, repo):
        repo.write(CONFIG, "")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n  config.yaml holds no settings"
        )


class TestRulesetLoader:
    def test_local_ruleset_loads_bindings_by_file(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(
            ".codeguard/bindings/python/placement.yaml",
            "skill: .claude/skills/responsibility-placement\n"
            "paths: [app/**/*.py]\nseverity: warning\ntriggers: [any]\n",
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset == Ruleset(
            name=None,
            root=repo.root / ".codeguard",
            bindings=BindingsConfig(
                {
                    "python/placement.yaml": BindingConfig(
                        triggers=frozenset({"any"}),
                        skill=repo.root / ".claude/skills/responsibility-placement",
                        paths=("app/**/*.py",),
                        severity=Severity.WARNING,
                    )
                }
            ),
        )

    def test_binding_file_may_end_in_yml(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(
            ".codeguard/bindings/placement.yml",
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\ntriggers: [any]\n',
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.judged_rule_ids() == {"responsibility-placement"}

    def test_skill_bound_in_a_yaml_and_a_yml_file_is_an_error(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        binding = 'skill: .claude/skills/responsibility-placement\npaths: ["**"]\ntriggers: [any]\n'
        repo.write(BINDING, binding)
        repo.write(".codeguard/bindings/placement.yml", binding)

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            f"  bindings: Value error, skill {repo.root}/.claude/skills/responsibility-placement "
            "is bound more than once: placement.yaml, placement.yml"
        )

    def test_loads_the_binding_model(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\ntriggers: [any]\n'
            "model: claude-haiku-5-5\n",
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.bindings.root["placement.yaml"].model == "claude-haiku-5-5"

    def test_loads_the_binding_provider(self, repo, make_skill, make_binding_config):
        repo.write(SKILL, make_skill().text)
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\ntriggers: [any]\n'
            "provider: gemini\nmodel: gemini-3.1-pro-preview\n",
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.bindings.root["placement.yaml"] == make_binding_config(
            skill=repo.root / ".claude/skills/responsibility-placement",
            provider=JudgeProvider.GEMINI,
            model="gemini-3.1-pro-preview",
        )

    def test_loads_the_binding_triggers(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\ntriggers: [any]\n'
            "triggers: [class-header, fixture]\n",
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.bindings.root["placement.yaml"].triggers == {
            ChangeKind.CLASS_HEADER,
            ChangeKind.FIXTURE,
        }

    def test_binding_without_triggers_triggers_on_any_change(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(BINDING, 'skill: .claude/skills/responsibility-placement\npaths: ["**"]\n')

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.bindings.root["placement.yaml"].triggers == {ChangeKind.ANY}

    def test_trigger_that_is_no_change_kind_or_gate_is_an_error(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\n'
            "triggers: [enum-value, fixture]\n",
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.placement.yaml.triggers: no change kind or gate enum-value"
        )

    def test_trigger_names_a_gate_of_the_ruleset(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(".codeguard/gates/enum-value.yml", ENUM_VALUE_GATE)
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\n'
            "triggers: [enum-value]\n",
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.selected_bindings()["responsibility-placement"].triggers == {
            "gate:enum-value"
        }

    def test_ci_only_rule_is_selected_in_ci(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(BINDING, 'skill: .claude/skills/responsibility-placement\npaths: ["**"]\n')
        ruleset = replace(
            RulesetLoader.local(repo.root).load(), selection=RulesetConfig(ci_only=True)
        )

        assert list(ruleset.selected_bindings()) == ["responsibility-placement"]

    def test_ci_only_rule_is_not_selected_when_skipped(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(BINDING, 'skill: .claude/skills/responsibility-placement\npaths: ["**"]\n')
        ruleset = replace(
            RulesetLoader.local(repo.root).load(),
            selection=RulesetConfig(ci_only=True),
            skip_ci_only=True,
        )

        assert ruleset.selected_bindings() == {}

    def test_gate_named_after_a_change_kind_is_an_error(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(
            ".codeguard/gates/fixture.yml",
            "id: fixture\nlanguage: python\nrule:\n  kind: decorator\n",
        )
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\ntriggers: [fixture]\n',
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n  gates.fixture: a change kind has this name"
        )

    def test_gate_with_a_pattern_rule_id_is_an_error(self, repo):
        repo.write(
            ".codeguard/gates/no-print.yml",
            "id: no-print\nlanguage: python\nrule:\n  pattern: print($$$A)\n",
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n  gates.no-print: a pattern rule has this id"
        )

    def test_project_without_bindings_has_none(self, repo):
        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.bindings == BindingsConfig({})

    def test_package_skill_is_under_the_package(self, tmp_path, make_skill):
        (tmp_path / "python/skills/placement").mkdir(parents=True)
        (tmp_path / "python/skills/placement/SKILL.md").write_text(make_skill().text)
        (tmp_path / "python/bindings").mkdir()
        (tmp_path / "python/bindings/placement.yaml").write_text(
            'skill: python/skills/placement\npaths: ["**"]\ntriggers: [any]\n'
        )

        ruleset = RulesetLoader(repo=tmp_path, root=tmp_path / "python").load()

        assert ruleset == Ruleset(
            name=None,
            root=tmp_path / "python",
            bindings=BindingsConfig(
                {
                    "placement.yaml": BindingConfig(
                        triggers=frozenset({"any"}),
                        skill=tmp_path / "python/skills/placement",
                        paths=("**",),
                    )
                }
            ),
        )

    def test_errors_name_the_binding_file(self, repo, make_skill):
        repo.write(SKILL, make_skill().text)
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npath: ["**"]\nseverity: fatal\n'
            "triggers: [any]\n",
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.placement.yaml.paths: Field required\n"
            "  bindings.placement.yaml.severity: "
            "Input should be 'error', 'warning', 'info' or 'hint'\n"
            "  bindings.placement.yaml.path: Extra inputs are not permitted"
        )

    def test_loads_a_pattern_rule_binding(self, repo):
        repo.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        repo.write(
            ".codeguard/bindings/no-print.yaml",
            'rule: no-print\npaths: ["**/*.py"]\nexclude_paths: ["tests/**"]\n',
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.pattern_bindings == PatternBindingsConfig(
            {
                "no-print.yaml": PatternBindingConfig(
                    rule="no-print", paths=("**/*.py",), exclude_paths=("tests/**",)
                )
            }
        )

    def test_binding_for_a_missing_pattern_rule_is_an_error(self, repo):
        repo.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        repo.write(".codeguard/bindings/no-prnt.yaml", 'rule: no-prnt\npaths: ["**"]\n')

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.no-prnt.yaml.rule: no pattern rule no-prnt"
        )

    def test_pattern_rule_bound_twice_is_an_error(self, repo):
        repo.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        repo.write(".codeguard/bindings/a.yaml", 'rule: no-print\npaths: ["**"]\n')
        repo.write(".codeguard/bindings/b.yaml", 'rule: no-print\npaths: ["**"]\n')

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings: Value error, rule no-print is bound more than once: a.yaml, b.yaml"
        )

    def test_missing_skill_is_an_error(self, repo):
        repo.write(
            BINDING,
            'skill: .claude/skills/responsibility-placement\npaths: ["**"]\ntriggers: [any]\n',
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.placement.yaml.skill: Path does not point to a directory"
        )
