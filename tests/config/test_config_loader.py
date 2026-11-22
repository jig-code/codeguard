import os
import shutil
from pathlib import Path
from unittest import mock

import pytest
import yaml

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
FULL_CONFIG = Path(__file__).parents[1] / "data/config.yaml"
BINDING = ".codeguard/bindings/placement.yaml"
JUDGE_RULE = ".codeguard/rules/judge/responsibility-placement.md"
ENUM_VALUE_GATE = {"id": "enum-value", "language": "python", "rule": {"pattern": "$X.value"}}
NO_PRINT_RULE = {"id": "no-print", "language": "python", "rule": {"pattern": "print($$$)"}}


class TestConfigLoader:
    def test_project_without_config_has_the_defaults(self, repo):
        config = ConfigLoader(repo.root).load()

        assert config == Config()

    @mock.patch.dict(os.environ, {"CODEGUARD_CONFIG": "codeguard.local.yaml"})
    def test_env_var_names_the_config_file_to_load(self, repo):
        repo.write(CONFIG, yaml.safe_dump({"review_time_limit_minutes": 10}))
        repo.write("codeguard.local.yaml", yaml.safe_dump({"review_time_limit_minutes": 20}))

        assert ConfigLoader(repo.root).load().review_time_limit_minutes == 20

    def test_gemini_settings_in_the_config_file_are_an_error(self, repo):
        repo.write(CONFIG, yaml.safe_dump({"judge": {"gemini": {"project": "my-project"}}}))

        with pytest.raises(ConfigError) as error:
            ConfigLoader(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n  judge.gemini: Extra inputs are not permitted"
        )

    def test_loads_every_setting_of_the_config_file(self, repo):
        shutil.copy(FULL_CONFIG, repo.root / CONFIG)

        config = ConfigLoader(repo.root).load()

        assert config == Config(
            review_time_limit_minutes=10,
            judge=JudgeConfig(
                provider=JudgeProvider.BEDROCK,
                model="project-model",
                thinking=ThinkingConfig(claude_cli="high", gemini="low"),
            ),
            packages=(
                PathPackageConfig(
                    path=Path("rules"), rulesets={"python": RulesetConfig(exclude=("no-print",))}
                ),
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
            yaml.safe_dump(
                {
                    "rule": "responsibility-placement",
                    "paths": ["app/**/*.py"],
                    "severity": "warning",
                    "triggers": ["any"],
                }
            ),
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
            yaml.safe_dump(
                {"rule": "responsibility-placement", "paths": ["**"], "triggers": ["any"]}
            ),
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.judged_rule_ids() == {"responsibility-placement"}

    def test_rule_bound_in_a_yaml_and_a_yml_file_is_an_error(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        binding = yaml.safe_dump(
            {"rule": "responsibility-placement", "paths": ["**"], "triggers": ["any"]}
        )
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
            yaml.safe_dump(
                {
                    "rule": "responsibility-placement",
                    "paths": ["**"],
                    "triggers": ["enum-value", "fixture"],
                }
            ),
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.placement.yaml.triggers: no change kind or gate enum-value"
        )

    def test_trigger_names_a_gate_of_the_ruleset(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_VALUE_GATE))
        repo.write(
            BINDING,
            yaml.safe_dump(
                {"rule": "responsibility-placement", "paths": ["**"], "triggers": ["enum-value"]}
            ),
        )

        ruleset = RulesetLoader.local(repo.root).load()

        assert ruleset.selected_bindings()["responsibility-placement"].triggers == {
            "gate:enum-value"
        }

    def test_gate_named_after_a_change_kind_is_an_error(self, repo, make_judge_rule):
        repo.write(JUDGE_RULE, make_judge_rule().text)
        repo.write(
            ".codeguard/gates/fixture.yml",
            yaml.safe_dump({"id": "fixture", "language": "python", "rule": {"kind": "decorator"}}),
        )
        repo.write(
            BINDING,
            yaml.safe_dump(
                {"rule": "responsibility-placement", "paths": ["**"], "triggers": ["fixture"]}
            ),
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n  gates.fixture: a change kind has this name"
        )

    def test_gate_with_a_pattern_rule_id_is_an_error(self, repo):
        repo.write(
            ".codeguard/gates/no-print.yml",
            yaml.safe_dump(
                {"id": "no-print", "language": "python", "rule": {"pattern": "print($$$A)"}}
            ),
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
            yaml.safe_dump({"rule": "placement", "paths": ["**"], "triggers": ["any"]})
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
            yaml.safe_dump(
                {
                    "rule": "responsibility-placement",
                    "path": ["**"],
                    "severity": "fatal",
                    "triggers": ["any"],
                }
            ),
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
        repo.write(".codeguard/rules/pattern/no-print.yml", yaml.safe_dump(NO_PRINT_RULE))
        repo.write(
            ".codeguard/bindings/no-print.yaml",
            yaml.safe_dump(
                {"rule": "no-print", "paths": ["**/*.py"], "exclude_paths": ["tests/**"]}
            ),
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
        repo.write(".codeguard/rules/pattern/no-print.yml", yaml.safe_dump(NO_PRINT_RULE))
        repo.write(
            ".codeguard/bindings/no-prnt.yaml", yaml.safe_dump({"rule": "no-prnt", "paths": ["**"]})
        )

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
        repo.write(".codeguard/rules/pattern/no-print.yml", yaml.safe_dump(NO_PRINT_RULE))
        repo.write(".codeguard/rules/judge/no-print.md", make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/no-print.yaml",
            yaml.safe_dump({"rule": "no-print", "paths": ["**"]}),
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.no-print.yaml.rule: "
            "both rules/judge/no-print.md and pattern rule no-print have this id"
        )

    def test_malformed_pattern_rule_file_is_a_config_error(self, repo, make_judge_rule):
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(".codeguard/rules/pattern/bad.yaml", yaml.safe_dump({"bogus": 1}))
        repo.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump({"rule": "placement", "paths": ["**"]}),
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == f"{repo.root}/.codeguard is invalid:\n  rules.id: Field required"

    @pytest.mark.parametrize(
        "rule", ["../../../placement", "..\\..\\..\\placement"], ids=["slash", "backslash"]
    )
    def test_rule_id_that_is_a_path_is_an_error(self, repo, make_judge_rule, rule):
        repo.write("placement.md", make_judge_rule().text)
        repo.write(BINDING, yaml.safe_dump({"rule": rule, "paths": ["**"], "triggers": ["any"]}))

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            f"  bindings.placement.yaml.rule: {rule!r} is not a rule id"
        )

    def test_legacy_skill_binding_that_also_names_a_pattern_rule_is_an_error(
        self, repo, make_judge_rule
    ):
        repo.write(".codeguard/rules/pattern/no-print.yml", yaml.safe_dump(NO_PRINT_RULE))
        repo.write(".codeguard/skills/no-print/SKILL.md", make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/no-print.yaml",
            yaml.safe_dump(
                {"rule": "no-print", "skill": ".codeguard/skills/no-print", "paths": ["**"]}
            ),
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.no-print.yaml: Value error, rule and skill both name a rule: "
            "keep only rule"
        )

    def test_pattern_rule_bound_twice_is_an_error(self, repo):
        repo.write(".codeguard/rules/pattern/no-print.yml", yaml.safe_dump(NO_PRINT_RULE))
        repo.write(
            ".codeguard/bindings/a.yaml", yaml.safe_dump({"rule": "no-print", "paths": ["**"]})
        )
        repo.write(
            ".codeguard/bindings/b.yaml", yaml.safe_dump({"rule": "no-print", "paths": ["**"]})
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings: Value error, rule no-print is bound more than once: a.yaml, b.yaml"
        )

    def test_binding_for_a_missing_judge_rule_is_an_error(self, repo):
        repo.write(
            BINDING,
            yaml.safe_dump(
                {"rule": "responsibility-placement", "paths": ["**"], "triggers": ["any"]}
            ),
        )

        with pytest.raises(ConfigError) as error:
            RulesetLoader.local(repo.root).load()

        assert str(error.value) == (
            f"{repo.root}/.codeguard is invalid:\n"
            "  bindings.placement.yaml.rule: no judge rule "
            "rules/judge/responsibility-placement.md or pattern rule responsibility-placement"
        )

    def test_legacy_skill_directory_in_a_package_is_under_the_package(
        self, tmp_path, make_judge_rule
    ):
        (tmp_path / "python/skills/placement").mkdir(parents=True)
        (tmp_path / "python/skills/placement/SKILL.md").write_text(make_judge_rule().text)
        (tmp_path / "python/bindings").mkdir()
        (tmp_path / "python/bindings/placement.yaml").write_text(
            yaml.safe_dump(
                {"skill": "python/skills/placement", "paths": ["**"], "triggers": ["any"]}
            )
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

    def test_legacy_skill_and_rule_file_bindings_may_share_a_ruleset(
        self, directory, make_judge_rule
    ):
        naming = make_judge_rule(name="naming", text="# Naming\n\nNames say what a value is.\n")
        directory.write("python/rules/judge/responsibility-placement.md", make_judge_rule().text)
        directory.write("python/skills/naming/SKILL.md", f"---\nname: naming\n---\n{naming.text}")
        directory.write(
            "python/bindings/naming.yaml",
            yaml.safe_dump({"skill": "python/skills/naming", "paths": ["**"]}),
        )
        directory.write(
            "python/bindings/placement.yaml",
            yaml.safe_dump({"rule": "responsibility-placement", "paths": ["**"]}),
        )

        ruleset = RulesetLoader(repo=directory.root, root=directory.root / "python").load()

        by_file = ruleset.bindings.root
        assert ruleset.judge_rule_text(by_file["naming.yaml"]) == naming.text
        assert ruleset.judge_rule_text(by_file["placement.yaml"]) == make_judge_rule().text
