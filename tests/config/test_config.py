from pathlib import Path

import pytest
from packaging.version import Version
from pydantic import ValidationError
from rules_package import NO_PRINT_RULE

from codeguard.config import (
    BindingConfig,
    BindingsConfig,
    Config,
    ConfigError,
    GitPackageConfig,
    JudgeChoice,
    JudgeConfig,
    JudgeModel,
    JudgeProvider,
    PatternRule,
    RuleOverride,
    RulesetConfig,
    Severity,
)

CPUS = 7


def messages(error: pytest.ExceptionInfo[ValidationError]) -> list[str]:
    return [problem["msg"] for problem in error.value.errors()]


@pytest.fixture
def placement_skill(tmp_path) -> Path:
    (tmp_path / "placement").mkdir()
    (tmp_path / "placement/SKILL.md").write_text("# Placement\n")
    return tmp_path / "placement"


class TestBindingsConfig:
    def test_skill_directory_is_under_the_working_tree(self, tmp_path, placement_skill):
        bindings = BindingsConfig.model_validate(
            {"placement.yaml": {"skill": "placement", "paths": ["**"], "triggers": ["any"]}},
            context={"working_tree": tmp_path},
        )

        assert bindings.root["placement.yaml"] == BindingConfig(
            skill=placement_skill, paths=("**",), triggers=frozenset({"any"})
        )

    def test_skill_directory_names_the_rule(self, placement_skill):
        binding = BindingConfig(skill=placement_skill, paths=("**",))

        assert binding.rule_id == "placement"

    def test_skill_directory_without_skill_file_is_an_error(self, tmp_path):
        (tmp_path / "placement").mkdir()

        with pytest.raises(ValidationError) as error:
            BindingsConfig.model_validate(
                {"placement.yaml": {"skill": "placement", "paths": ["**"], "triggers": ["any"]}},
                context={"working_tree": tmp_path},
            )

        assert messages(error) == [f"Value error, {tmp_path}/placement has no SKILL.md"]

    def test_binding_naming_a_rule_and_a_skill_is_an_error(self, placement_skill):
        with pytest.raises(ValidationError) as error:
            BindingConfig.model_validate(
                {"rule": "placement", "skill": placement_skill, "paths": ["**"]}
            )

        assert messages(error) == ["Value error, rule and skill both name a rule: keep only rule"]

    def test_binding_reads_its_provider_model_and_triggers(self, make_binding_config):
        binding = BindingConfig.model_validate(
            {
                "rule": "responsibility-placement",
                "paths": ["**"],
                "triggers": ["class-header", "fixture"],
                "provider": "gemini",
                "model": "gemini-judge-test",
            }
        )

        assert binding == make_binding_config(
            triggers=frozenset({"class-header", "fixture"}),
            provider=JudgeProvider.GEMINI,
            model="gemini-judge-test",
        )

    def test_binding_naming_no_rule_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            BindingConfig.model_validate({"paths": ["**"]})

        assert messages(error) == ["Value error, name the rule with rule: <id>"]

    def test_retired_disable_skips_is_ignored(self):
        bindings = BindingsConfig.model_validate(
            {
                "placement.yaml": {
                    "rule": "placement",
                    "paths": ["**"],
                    "triggers": ["any"],
                    "disable_skips": ["renames"],
                }
            }
        )

        assert bindings.root["placement.yaml"] == BindingConfig(
            triggers=frozenset({"any"}), rule="placement", paths=("**",)
        )

    def test_rule_bound_twice_is_an_error(self):
        binding = {"rule": "placement", "paths": ["**"], "triggers": ["any"]}

        with pytest.raises(ValidationError) as error:
            BindingsConfig.model_validate({"a.yaml": binding, "b.yaml": binding})

        assert messages(error) == [
            "Value error, rule placement is bound more than once: a.yaml, b.yaml"
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

    def test_listed_rulesets_run_every_rule(self):
        config = Config.model_validate(
            {
                "packages": [
                    {
                        "kind": "git",
                        "git": "https://example.com/rules.git",
                        "ref": "v1.0.0",
                        "rulesets": ["general", "python"],
                    }
                ]
            }
        )

        assert config.packages == (
            GitPackageConfig(
                git="https://example.com/rules.git",
                ref="v1.0.0",
                rulesets={"general": RulesetConfig(), "python": RulesetConfig()},
            ),
        )

    def test_ruleset_listed_twice_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            Config.model_validate(
                {
                    "packages": [
                        {
                            "kind": "git",
                            "git": "https://example.com/rules.git",
                            "ref": "v1.0.0",
                            "rulesets": ["python", "python"],
                        }
                    ]
                }
            )

        assert messages(error) == ["Value error, rulesets listed more than once: python"]

    def test_empty_ruleset_list_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            Config.model_validate(
                {
                    "packages": [
                        {
                            "kind": "git",
                            "git": "https://example.com/rules.git",
                            "ref": "v1.0.0",
                            "rulesets": [],
                        }
                    ]
                }
            )

        assert messages(error) == ["Value should have at least 1 item after validation, not 0"]

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

    def test_override_replaces_only_the_fields_it_sets(self):
        bindings = BindingsConfig.model_validate(
            {
                "placement.yaml": {
                    "rule": "placement",
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
            rule="placement",
            paths=("**",),
            severity=Severity.WARNING,
            model="claude-haiku-5-5",
        )

    def test_ruleset_severity_applies_to_a_rule_without_an_override(self):
        bindings = BindingsConfig.model_validate(
            {"placement.yaml": {"rule": "placement", "paths": ["**"], "triggers": ["any"]}}
        )

        binding = RulesetConfig(severity=Severity.WARNING).apply(
            "placement", bindings.root["placement.yaml"]
        )

        assert binding == BindingConfig(
            triggers=frozenset({"any"}), rule="placement", paths=("**",), severity=Severity.WARNING
        )

    def test_rule_override_severity_wins_over_the_ruleset_severity(self):
        bindings = BindingsConfig.model_validate(
            {
                "placement.yaml": {
                    "rule": "placement",
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
            triggers=frozenset({"any"}), rule="placement", paths=("**",), severity=Severity.ERROR
        )

    def test_rule_override_without_severity_takes_the_ruleset_severity(self):
        bindings = BindingsConfig.model_validate(
            {"placement.yaml": {"rule": "placement", "paths": ["**"], "triggers": ["any"]}}
        )
        selection = RulesetConfig(
            severity=Severity.WARNING, rules={"placement": RuleOverride(paths=("app/**",))}
        )

        binding = selection.apply("placement", bindings.root["placement.yaml"])

        assert binding == BindingConfig(
            triggers=frozenset({"any"}),
            rule="placement",
            paths=("app/**",),
            severity=Severity.WARNING,
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

    def test_codex_binding_uses_its_selected_model(self):
        binding = BindingConfig.model_validate(
            {
                "rule": "placement",
                "paths": ["**/*.py"],
                "provider": "codex-cli",
                "model": "a-bound-model",
            }
        )

        assert binding.judge == JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="a-bound-model")


class TestRuleset:
    def test_packaged_rule_is_named_by_its_ruleset(self, make_ruleset, make_binding_config):
        ruleset = make_ruleset(name="example/python")

        assert ruleset.selected_bindings() == {
            "example/python/responsibility-placement": make_binding_config()
        }

    def test_excluded_rule_is_dropped(self, make_ruleset):
        ruleset = make_ruleset(selection=RulesetConfig(exclude=("responsibility-placement",)))

        assert ruleset.selected_bindings() == {}

    def test_rule_left_out_of_include_is_dropped(self, make_ruleset):
        ruleset = make_ruleset(selection=RulesetConfig(include=("another-rule",)))

        assert ruleset.selected_bindings() == {}

    def test_included_rule_is_kept(self, make_ruleset, make_binding_config):
        ruleset = make_ruleset(selection=RulesetConfig(include=("responsibility-placement",)))

        assert ruleset.selected_bindings() == {"responsibility-placement": make_binding_config()}

    def test_override_replaces_the_binding_fields(self, make_ruleset, make_binding_config):
        override = RuleOverride(paths=("app/**",), severity=Severity.WARNING)
        ruleset = make_ruleset(
            selection=RulesetConfig(rules={"responsibility-placement": override})
        )

        assert ruleset.selected_bindings() == {
            "responsibility-placement": make_binding_config(
                paths=("app/**",), severity=Severity.WARNING
            )
        }

    def test_override_replaces_the_excluded_paths(self, make_ruleset, make_binding_config):
        override = RuleOverride(exclude_paths=())
        ruleset = make_ruleset(
            binding__exclude_paths=("tests/**",),
            selection=RulesetConfig(rules={"responsibility-placement": override}),
        )

        assert ruleset.selected_bindings() == {"responsibility-placement": make_binding_config()}

    def test_ci_only_rule_is_selected_in_ci(self, make_ruleset, make_binding_config):
        ruleset = make_ruleset(selection=RulesetConfig(ci_only=True))

        assert ruleset.selected_bindings() == {"responsibility-placement": make_binding_config()}

    def test_ci_only_rule_is_not_selected_when_skipped(self, make_ruleset):
        ruleset = make_ruleset(selection=RulesetConfig(ci_only=True), skip_ci_only=True)

        assert ruleset.selected_bindings() == {}

    def test_package_default_judges_its_rules(self, make_ruleset, make_binding_config):
        package = JudgeChoice(provider=JudgeProvider.BEDROCK, model="package-model")
        ruleset = make_ruleset(package_judge=package)

        judge = ruleset.judge_choice(make_binding_config(), JudgeChoice(), JudgeChoice())

        assert judge == package

    def test_project_default_wins_over_the_package_default(self, make_ruleset, make_binding_config):
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(package_judge=package)

        judge = ruleset.judge_choice(make_binding_config(), project, JudgeChoice())

        assert judge == project

    def test_binding_wins_over_the_project_default(self, make_ruleset, make_binding_config):
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        binding = make_binding_config(provider=JudgeProvider.GEMINI, model="bound-model")

        judge = make_ruleset().judge_choice(binding, project, JudgeChoice())

        assert judge == JudgeChoice(provider=JudgeProvider.GEMINI, model="bound-model")

    def test_provider_and_model_each_come_from_the_first_level_naming_it(
        self, make_ruleset, make_binding_config
    ):
        package = JudgeChoice(model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK)
        binding = make_binding_config(model="bound-model")

        judge = make_ruleset(package_judge=package).judge_choice(binding, project, JudgeChoice())

        assert judge == JudgeChoice(provider=JudgeProvider.BEDROCK, model="bound-model")

    def test_project_model_runs_on_the_package_provider(self, make_ruleset, make_binding_config):
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(model="project-model")

        judge = make_ruleset(package_judge=package).judge_choice(
            make_binding_config(), project, JudgeChoice()
        )

        assert judge == JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="project-model")

    def test_override_naming_a_provider_replaces_every_level(
        self, make_ruleset, make_binding_config
    ):
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        binding = make_binding_config(provider=JudgeProvider.GEMINI, model="bound-model")
        override = JudgeChoice(provider=JudgeProvider.CLAUDE_CLI)

        judge = make_ruleset().judge_choice(binding, project, override)

        assert judge == override

    def test_gates_are_not_pattern_rules(self, directory, make_ruleset):
        directory.write("rules/pattern/no-print.yml", NO_PRINT_RULE)
        directory.write(
            "gates/enum-value.yml",
            "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n",
        )

        rules = make_ruleset(root=directory.root).pattern_rules()

        assert rules == [
            PatternRule.model_validate(
                {
                    "id": "no-print",
                    "metadata": {
                        "why": "Print output skips the log levels and handlers production reads."
                    },
                }
            )
        ]

    def test_malformed_pattern_rule_file_is_a_config_error(self, directory, make_ruleset):
        directory.write("rules/pattern/bad.yml", "bogus: 1\n")

        with pytest.raises(ConfigError) as error:
            make_ruleset(root=directory.root).pattern_rules()

        assert str(error.value) == f"{directory.root} is invalid:\n  rules.id: Field required"

    def test_rule_file_text_reaches_the_judge_unparsed(
        self, directory, make_ruleset, make_binding_config, make_judge_rule
    ):
        text = f"---\nname: responsibility-placement\n---\n{make_judge_rule().text}"
        directory.write("rules/judge/responsibility-placement.md", text)

        judge_text = make_ruleset(root=directory.root).judge_rule_text(make_binding_config())

        assert judge_text == text

    def test_skill_file_reaches_the_judge_without_its_frontmatter(
        self, directory, make_ruleset, make_binding_config, make_judge_rule
    ):
        directory.write(
            "skills/placement/SKILL.md",
            f"---\nname: placement\n---\n{make_judge_rule().text}",
        )
        binding = make_binding_config(rule=None, skill=directory.root / "skills/placement")

        judge_text = make_ruleset(root=directory.root).judge_rule_text(binding)

        assert judge_text == make_judge_rule().text


class TestPatternRule:
    @pytest.mark.parametrize(
        "metadata",
        [None, {"source": "https://example.com"}, {"why": ""}, {"why": "  "}],
        ids=["no-metadata", "source-only", "empty-why", "blank-why"],
    )
    def test_pattern_rule_without_a_why_text_does_not_say_why(self, metadata):
        rule = PatternRule.model_validate({"id": "no-print", "metadata": metadata})

        assert not rule.says_why

    def test_pattern_rule_with_a_why_says_why(self):
        rule = PatternRule.model_validate(
            {"id": "no-print", "metadata": {"why": "Print skips the log levels."}}
        )

        assert rule.says_why

    def test_why_that_is_not_text_is_an_error(self):
        with pytest.raises(ValidationError) as error:
            PatternRule.model_validate({"id": "no-print", "metadata": {"why": 1}})

        assert error.value.errors(include_url=False, include_input=False) == [
            {
                "type": "string_type",
                "loc": ("metadata", "why"),
                "msg": "Input should be a valid string",
            }
        ]


class TestJudgeChoice:
    def test_choice_naming_nothing_runs_the_claude_cli_with_no_model(self):
        assert JudgeChoice().judge_model == JudgeModel(provider=JudgeProvider.CLAUDE_CLI)

    def test_claude_model_with_no_provider_named_runs_on_the_claude_cli(self):
        judge = JudgeChoice(model="claude-haiku-5-5")

        assert judge.judge_model == JudgeModel(
            provider=JudgeProvider.CLAUDE_CLI, name="claude-haiku-5-5"
        )

    @pytest.mark.parametrize("provider", [JudgeProvider.CODEX_CLI, JudgeProvider.GEMINI])
    def test_provider_other_than_the_claude_cli_without_a_model_is_an_error(self, provider):
        with pytest.raises(ConfigError) as error:
            _ = JudgeChoice(provider=provider).judge_model

        assert str(error.value) == (
            f"provider {provider} needs a model: set model in the rule's binding, "
            "judge.model in .codeguard/config.yaml (or CODEGUARD_JUDGE__MODEL), or "
            "judge.model in its package's codeguard-package.yaml"
        )

    @pytest.mark.parametrize("model", ["gpt-6-luna", "o9-mini"])
    def test_model_other_than_claude_with_no_provider_named_is_an_error(self, model):
        with pytest.raises(ConfigError) as error:
            _ = JudgeChoice(model=model).judge_model

        assert str(error.value) == (
            f"model {model} needs a provider: set provider in the rule's binding, "
            "judge.provider in .codeguard/config.yaml (or CODEGUARD_JUDGE__PROVIDER), or "
            "judge.provider in its package's codeguard-package.yaml"
        )

    @pytest.mark.parametrize(
        ("provider", "model"),
        [
            (JudgeProvider.CLAUDE_CLI, "gpt-6-luna"),
            (JudgeProvider.BEDROCK, JudgeProvider.GEMINI.default_model),
        ],
    )
    def test_model_the_provider_cant_run_is_an_error(self, provider, model):
        with pytest.raises(ConfigError) as error:
            _ = JudgeChoice(provider=provider, model=model).judge_model

        assert str(error.value) == f"provider {provider} can't run model {model}"

    def test_model_of_a_family_the_provider_runs_is_its_judge(self):
        judge = JudgeChoice(provider=JudgeProvider.BEDROCK, model="gpt-6-luna")

        assert judge.judge_model == JudgeModel(provider=JudgeProvider.BEDROCK, name="gpt-6-luna")

    def test_model_of_no_known_family_is_its_judge(self):
        profile = "arn:aws:bedrock:us-west-2:1:application-inference-profile/x"

        judge = JudgeChoice(provider=JudgeProvider.BEDROCK, model=profile)

        assert judge.judge_model == JudgeModel(provider=JudgeProvider.BEDROCK, name=profile)

    def test_required_name_of_a_model_left_unnamed_is_an_error(self):
        with pytest.raises(ConfigError) as error:
            _ = JudgeModel(provider=JudgeProvider.GEMINI).required_name

        assert str(error.value) == (
            "provider gemini needs a model: set model in the rule's binding, "
            "judge.model in .codeguard/config.yaml (or CODEGUARD_JUDGE__MODEL), or "
            "judge.model in its package's codeguard-package.yaml"
        )


class TestJudgeConfig:
    def test_claude_runs_a_call_per_cpu_at_once(self):
        assert JudgeConfig().concurrency(JudgeProvider.CLAUDE_CLI, CPUS) == CPUS

    def test_gemini_runs_two_calls_at_once(self):
        assert JudgeConfig().concurrency(JudgeProvider.GEMINI, CPUS) == 2

    def test_calls_at_once_sets_the_concurrency(self):
        assert JudgeConfig(calls_at_once=1).concurrency(JudgeProvider.GEMINI, CPUS) == 1

    @pytest.mark.parametrize("provider", [JudgeProvider.CLAUDE_CLI, JudgeProvider.CODEX_CLI])
    def test_calls_at_once_is_ignored_on_a_cli(self, provider):
        assert JudgeConfig(calls_at_once=1).concurrency(provider, CPUS) == CPUS

    def test_calls_at_once_is_ignored_on_bedrock(self):
        assert JudgeConfig(calls_at_once=5).concurrency(JudgeProvider.BEDROCK, CPUS) == 2

    def test_a_cli_without_a_cpu_count_runs_one_call_at_once(self):
        assert JudgeConfig().concurrency(JudgeProvider.CLAUDE_CLI, None) == 1


def test_codex_concurrency_uses_the_cli_limit():
    assert JudgeConfig().concurrency(JudgeProvider.CODEX_CLI, CPUS) == CPUS
