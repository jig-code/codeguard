import os
from pathlib import Path
from unittest import mock

import pytest

from codeguard.config import (
    BindingConfig,
    BindingsConfig,
    Config,
    ConfigError,
    ConfigLoader,
    JudgeConfig,
    JudgeProvider,
    PathPackageConfig,
    PatternBindingConfig,
    PatternBindingsConfig,
    Ruleset,
    RulesetConfig,
    RulesetLoader,
    Severity,
    ThinkingConfig,
)

CONFIG = ".codeguard/config.yaml"
BINDING = ".codeguard/bindings/placement.yaml"
JUDGE_RULE = ".codeguard/rules/judge/responsibility-placement.md"
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

    @mock.patch.dict(os.environ, {"CODEGUARD_CONFIG": "codeguard.local.yaml"})
    def test_env_var_names_the_config_file_to_load(self, repo):
        repo.write(CONFIG, "review_time_limit_minutes: 10\n")
        repo.write("codeguard.local.yaml", "review_time_limit_minutes: 20\n")

        assert ConfigLoader(repo.root).load().review_time_limit_minutes == 20

    def test_gemini_settings_in_the_config_file_are_an_error(self, repo):
        repo.write(CONFIG, "judge:\n  gemini:\n    project: my-project\n")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n  judge.gemini: Extra inputs are not permitted"
        )

    def test_loads_the_project_judge_default(self, repo):
        repo.write(CONFIG, "judge:\n  provider: bedrock\n  model: project-model\n")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(
            provider=JudgeProvider.BEDROCK, model="project-model"
        )

    def test_loads_each_providers_thinking_level(self, repo):
        repo.write(CONFIG, "judge:\n  thinking:\n    claude-cli: high\n    gemini: low\n")

        thinking = ConfigLoader(repo.root).load().judge.thinking

        assert thinking == ThinkingConfig(
            claude_cli="high", codex_cli=None, gemini="low", bedrock="medium"
        )

    def test_thinking_level_for_an_unknown_provider_is_an_error(self, repo):
        repo.write(CONFIG, "judge:\n  thinking:\n    openai: high\n")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  judge.thinking.openai: Extra inputs are not permitted"
        )

    def test_unknown_thinking_level_is_an_error(self, repo):
        repo.write(CONFIG, "judge:\n  thinking:\n    gemini: max\n")

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value).startswith(
            f"{repo.root}/.codeguard is invalid:\n  judge.thinking.gemini: Input should be "
        )

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__THINKING__GEMINI": "high"})
    def test_thinking_level_in_the_environment_is_ignored(self, repo):
        repo.write(CONFIG, "judge:\n  thinking:\n    gemini: low\n")

        assert ConfigLoader(repo.root).load().judge.thinking.gemini == "low"

    @mock.patch.dict(
        os.environ, {"CODEGUARD_JUDGE__PROVIDER": "bedrock", "CODEGUARD_JUDGE__MODEL": "env-model"}
    )
    def test_judge_env_vars_override_the_file(self, repo):
        repo.write(CONFIG, "judge:\n  provider: codex-cli\n  model: file-model\n")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(
            provider=JudgeProvider.BEDROCK, model="env-model"
        )

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__MODEL": "env-model"})
    def test_judge_env_var_keeps_the_file_other_judge_settings(self, repo):
        repo.write(CONFIG, "judge:\n  calls_at_once: 1\n  model: file-model\n")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(
            calls_at_once=1, model="env-model"
        )

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__PROVIDER": "bedrock"})
    def test_judge_env_var_applies_without_a_config_file(self, repo):
        assert ConfigLoader(repo.root).load().judge == JudgeConfig(provider=JudgeProvider.BEDROCK)

    @mock.patch.dict(os.environ, {"CODEGUARD_CONFIDENCE_THRESHOLD": "0.8"})
    def test_env_var_for_another_setting_is_ignored(self, repo):
        repo.write(CONFIG, "confidence_threshold: 0.75\n")

        assert ConfigLoader(repo.root).load().confidence_threshold == 0.75

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__CALLS_AT_ONCE": "9"})
    def test_env_var_for_another_judge_setting_is_ignored(self, repo):
        repo.write(CONFIG, "judge:\n  calls_at_once: 1\n")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(calls_at_once=1)

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__MODEL": ""})
    def test_empty_judge_env_var_leaves_the_file_value(self, repo):
        repo.write(CONFIG, "judge:\n  model: file-model\n")

        assert ConfigLoader(repo.root).load().judge == JudgeConfig(model="file-model")

    @mock.patch.dict(os.environ, {"CODEGUARD_JUDGE__PROVIDER": "openai"})
    def test_unknown_judge_provider_in_the_environment_is_an_error(self, repo):
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
    def test_local_ruleset_loads_bindings_by_file(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/python/placement.yaml",
            "rule: responsibility-placement\n"
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
                        rule="responsibility-placement",
                        paths=("app/**/*.py",),
                        severity=Severity.WARNING,
                    )
                }
            ),
        )

    def test_binding_file_may_end_in_yml(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/placement.yml",
            'rule: responsibility-placement\npaths: ["**"]\ntriggers: [any]\n',
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.judged_rule_ids() == {"responsibility-placement"}

    def test_rule_bound_in_a_yaml_and_a_yml_file_is_an_error(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        binding = 'rule: responsibility-placement\npaths: ["**"]\ntriggers: [any]\n'
        repo.write(BINDING, binding)
        repo.write(".codeguard/bindings/placement.yml", binding)

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings: Value error, rule responsibility-placement "
            "is bound more than once: placement.yaml, placement.yml"
        )

    def test_trigger_that_is_no_change_kind_or_gate_is_an_error(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(
            BINDING,
            'rule: responsibility-placement\npaths: ["**"]\ntriggers: [enum-value, fixture]\n',
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.placement.yaml.triggers: no change kind or gate enum-value"
        )

    def test_trigger_names_a_gate_of_the_ruleset(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(".codeguard/gates/enum-value.yml", ENUM_VALUE_GATE)
        repo.write(
            BINDING,
            'rule: responsibility-placement\npaths: ["**"]\ntriggers: [enum-value]\n',
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.selected_bindings()["responsibility-placement"].triggers == {
            "gate:enum-value"
        }

    def test_gate_named_after_a_change_kind_is_an_error(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(
            ".codeguard/gates/fixture.yml",
            "id: fixture\nlanguage: python\nrule:\n  kind: decorator\n",
        )
        repo.write(
            BINDING,
            'rule: responsibility-placement\npaths: ["**"]\ntriggers: [fixture]\n',
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

    def test_package_rule_is_in_its_ruleset(self, tmp_path, make_judge_rule):
        (tmp_path / "python/rules/judge").mkdir(parents=True)
        (tmp_path / "python/rules/judge/placement.md").write_text(make_judge_rule().text)
        (tmp_path / "python/bindings").mkdir()
        (tmp_path / "python/bindings/placement.yaml").write_text(
            'rule: placement\npaths: ["**"]\ntriggers: [any]\n'
        )

        ruleset = RulesetLoader(repo=tmp_path, root=tmp_path / "python").load()

        assert ruleset == Ruleset(
            name=None,
            root=tmp_path / "python",
            bindings=BindingsConfig(
                {
                    "placement.yaml": BindingConfig(
                        triggers=frozenset({"any"}),
                        rule="placement",
                        paths=("**",),
                    )
                }
            ),
        )

    def test_errors_name_the_binding_file(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(
            BINDING,
            'rule: responsibility-placement\npath: ["**"]\nseverity: fatal\ntriggers: [any]\n',
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

    def test_binding_for_a_missing_rule_names_both_places_it_could_be(self, repo):
        repo.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        repo.write(".codeguard/bindings/no-prnt.yaml", 'rule: no-prnt\npaths: ["**"]\n')

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.no-prnt.yaml.rule: no judge rule rules/judge/no-prnt.md "
            "or pattern rule no-prnt"
        )

    def test_rule_id_of_both_a_judge_rule_and_a_pattern_rule_is_an_error(
        self, repo, make_judge_rule
    ):
        repo.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        repo.write(".codeguard/rules/judge/no-print.md", make_judge_rule().text)
        repo.write(".codeguard/bindings/no-print.yaml", 'rule: no-print\npaths: ["**"]\n')

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.no-print.yaml.rule: "
            "both rules/judge/no-print.md and pattern rule no-print have this id"
        )

    def test_malformed_pattern_rule_file_is_a_config_error(self, repo, make_judge_rule):
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(".codeguard/rules/pattern/bad.yaml", "bogus: 1\n")
        repo.write(".codeguard/bindings/placement.yaml", 'rule: placement\npaths: ["**"]\n')

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == f"{repo.root}/.codeguard is invalid:\n  rules.id: Field required"

    @pytest.mark.parametrize(
        "rule", ["../../../placement", "..\\..\\..\\placement"], ids=["slash", "backslash"]
    )
    def test_rule_id_that_is_a_path_is_an_error(self, repo, make_judge_rule, rule):
        repo.write("placement.md", make_judge_rule().text)
        repo.write(BINDING, f'rule: {rule}\npaths: ["**"]\ntriggers: [any]\n')

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            f"  bindings.placement.yaml.rule: {rule!r} is not a rule id"
        )

    def test_binding_naming_a_pattern_rule_and_a_skill_is_an_error(self, repo, make_judge_rule):
        repo.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        repo.write(".codeguard/skills/no-print/SKILL.md", make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/no-print.yaml",
            'rule: no-print\nskill: .codeguard/skills/no-print\npaths: ["**"]\n',
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.no-print.yaml: Value error, rule and skill both name a rule: "
            "keep only rule"
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

    def test_binding_for_a_missing_judge_rule_is_an_error(self, repo):
        repo.write(
            BINDING,
            'rule: responsibility-placement\npaths: ["**"]\ntriggers: [any]\n',
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.placement.yaml.rule: no judge rule "
            "rules/judge/responsibility-placement.md or pattern rule responsibility-placement"
        )

    def test_package_skill_directory_is_under_the_package(self, tmp_path, make_judge_rule):
        (tmp_path / "python/skills/placement").mkdir(parents=True)
        (tmp_path / "python/skills/placement/SKILL.md").write_text(make_judge_rule().text)
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

    def test_missing_skill_directory_is_an_error(self, repo):
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

    def test_ruleset_may_bind_rule_files_and_skill_directories_together(
        self, directory, make_judge_rule
    ):
        naming = make_judge_rule(name="naming", text="# Naming\n\nNames say what a value is.\n")
        directory.write("python/rules/judge/responsibility-placement.md", make_judge_rule().text)
        directory.write("python/skills/naming/SKILL.md", f"---\nname: naming\n---\n{naming.text}")
        directory.write(
            "python/bindings/naming.yaml", 'skill: python/skills/naming\npaths: ["**"]\n'
        )
        directory.write(
            "python/bindings/placement.yaml", 'rule: responsibility-placement\npaths: ["**"]\n'
        )

        ruleset = RulesetLoader(repo=directory.root, root=directory.root / "python").load()

        by_file = ruleset.bindings.root
        assert ruleset.judge_rule_text(by_file["naming.yaml"]) == naming.text
        assert ruleset.judge_rule_text(by_file["placement.yaml"]) == make_judge_rule().text
