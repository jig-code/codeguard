import pytest

from codeguard.config import (
    BindingConfig,
    BindingsConfig,
    ConfigError,
    JudgeChoice,
    JudgeModel,
    JudgeProvider,
    RuleOverride,
    Ruleset,
    RulesetConfig,
)
from codeguard.review import Binding, Bindings, Severity, Skill

SKILL_NAME = "responsibility-placement"


def write_skill(tmp_path, text: str):
    (tmp_path / SKILL_NAME).mkdir()
    (tmp_path / SKILL_NAME / "SKILL.md").write_text(text)
    return tmp_path / SKILL_NAME


def ruleset(
    tmp_path, skill, name=None, selection=RulesetConfig(), package_judge=JudgeChoice(), **binding
) -> Ruleset:
    bindings = BindingsConfig(
        {
            "placement.yaml": BindingConfig(
                triggers=frozenset({"any"}), skill=skill, paths=("**",), **binding
            )
        }
    )
    return Ruleset(
        name=name,
        root=tmp_path,
        bindings=bindings,
        selection=selection,
        package_judge=package_judge,
    )


class TestBinding:
    def test_files_matching_its_paths_are_kept(self, make_binding):
        binding = make_binding(paths=("app/**/*.py",))

        files = binding.files(["app/a.py", "app/models/b.py", "scripts/c.py"])

        assert files == ["app/a.py", "app/models/b.py"]

    def test_files_matching_its_exclude_paths_are_left_out(self, make_binding):
        binding = make_binding(paths=("**/*.py",), exclude_paths=("**/test_*.py",))

        files = binding.files(["app/a.py", "app/test_a.py", "app/b.rb"])

        assert files == ["app/a.py"]

    def test_from_config_has_its_exclude_paths(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        config = BindingConfig(
            triggers=frozenset({"any"}), skill=skill, paths=("**",), exclude_paths=("tests/**",)
        )

        binding = Binding.from_config(SKILL_NAME, config, JudgeChoice())

        assert binding == make_binding(exclude_paths=("tests/**",))

    def test_preset_binding_matches_every_file(self, make_binding):
        binding = make_binding()

        files = binding.files(["a.py", "app/b.rb"])

        assert files == ["a.py", "app/b.rb"]

    def test_from_config_builds_its_skill(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        config = BindingConfig(
            triggers=frozenset({"any"}), skill=skill, paths=("**",), severity=Severity.WARNING
        )

        binding = Binding.from_config(SKILL_NAME, config, JudgeChoice())

        assert binding == make_binding(severity=Severity.WARNING)

    def test_from_config_has_its_judge(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        config = BindingConfig(triggers=frozenset({"any"}), skill=skill, paths=("**",))
        judge = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="gpt-6-luna")

        binding = Binding.from_config(SKILL_NAME, config, judge)

        assert binding.model == JudgeModel(provider=JudgeProvider.CODEX_CLI, name="gpt-6-luna")


class TestBindings:
    def test_from_rulesets_builds_each_binding(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)

        bindings = Bindings.from_rulesets([ruleset(tmp_path, skill)])

        assert bindings == (make_binding(),)

    def test_packaged_binding_is_named_by_its_ruleset(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)

        bindings = Bindings.from_rulesets([ruleset(tmp_path, skill, name="example/python")])

        assert bindings == (make_binding(rule=f"example/python/{SKILL_NAME}"),)

    def test_excluded_binding_is_dropped(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        selection = RulesetConfig(exclude=(SKILL_NAME,))

        bindings = Bindings.from_rulesets([ruleset(tmp_path, skill, "example/python", selection)])

        assert bindings == ()

    def test_binding_left_out_of_include_is_dropped(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        selection = RulesetConfig(include=("another-rule",))

        bindings = Bindings.from_rulesets([ruleset(tmp_path, skill, "example/python", selection)])

        assert bindings == ()

    def test_included_binding_is_kept(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        selection = RulesetConfig(include=(SKILL_NAME,))

        bindings = Bindings.from_rulesets([ruleset(tmp_path, skill, "example/python", selection)])

        assert bindings == (make_binding(rule=f"example/python/{SKILL_NAME}"),)

    def test_override_replaces_the_binding_fields(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        override = RuleOverride(paths=("app/**",), severity=Severity.WARNING)
        selection = RulesetConfig(rules={SKILL_NAME: override})

        bindings = Bindings.from_rulesets([ruleset(tmp_path, skill, "example/python", selection)])

        assert bindings == (
            make_binding(
                rule=f"example/python/{SKILL_NAME}",
                paths=("app/**",),
                severity=Severity.WARNING,
            ),
        )

    def test_override_replaces_the_excluded_paths(self, tmp_path, make_binding, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        binding = BindingConfig(
            triggers=frozenset({"any"}), skill=skill, paths=("**",), exclude_paths=("tests/**",)
        )
        bindings = BindingsConfig({"placement.yaml": binding})
        selection = RulesetConfig(rules={SKILL_NAME: RuleOverride(exclude_paths=())})
        ruleset = Ruleset(name=None, root=tmp_path, bindings=bindings, selection=selection)

        assert Bindings.from_rulesets([ruleset]) == (make_binding(),)


class TestBindingsJudge:
    def test_rule_without_a_judge_named_runs_the_claude_cli_default(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)

        (binding,) = Bindings.from_rulesets([ruleset(tmp_path, skill)])

        assert binding.model == JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name=None)

    @pytest.mark.parametrize(
        "provider", [JudgeProvider.CODEX_CLI, JudgeProvider.GEMINI, JudgeProvider.BEDROCK]
    )
    def test_provider_other_than_the_claude_cli_without_a_model_is_an_error(
        self, tmp_path, make_skill, provider
    ):
        skill = write_skill(tmp_path, make_skill().text)
        (binding,) = Bindings.from_rulesets([ruleset(tmp_path, skill, provider=provider)])

        with pytest.raises(ConfigError) as error:
            _ = binding.model

        assert str(error.value) == (
            f"provider {provider} needs a model: set model in the rule's binding, "
            "judge.model in .codeguard/config.yaml (or CODEGUARD_JUDGE__MODEL), or "
            "judge.model in its package's codeguard-package.yaml"
        )

    def test_package_default_judges_its_rules(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(provider=JudgeProvider.BEDROCK, model="package-model")

        (binding,) = Bindings.from_rulesets([ruleset(tmp_path, skill, package_judge=package)])

        assert binding.model == JudgeModel(provider=JudgeProvider.BEDROCK, name="package-model")

    def test_project_default_wins_over_the_package_default(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")

        (binding,) = Bindings.from_rulesets(
            [ruleset(tmp_path, skill, package_judge=package)], project
        )

        assert binding.model == JudgeModel(provider=JudgeProvider.BEDROCK, name="project-model")

    def test_binding_wins_over_the_project_default(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        bound = ruleset(tmp_path, skill, provider=JudgeProvider.GEMINI, model="bound-model")

        (binding,) = Bindings.from_rulesets([bound], project)

        assert binding.model == JudgeModel(provider=JudgeProvider.GEMINI, name="bound-model")

    def test_provider_and_model_each_come_from_the_first_level_naming_it(
        self, tmp_path, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK)
        bound = ruleset(tmp_path, skill, package_judge=package, model="bound-model")

        (binding,) = Bindings.from_rulesets([bound], project)

        assert binding.model == JudgeModel(provider=JudgeProvider.BEDROCK, name="bound-model")

    def test_project_model_with_the_package_provider(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(model="project-model")

        (binding,) = Bindings.from_rulesets(
            [ruleset(tmp_path, skill, package_judge=package)], project
        )

        assert binding.model == JudgeModel(provider=JudgeProvider.CODEX_CLI, name="project-model")

    def test_override_naming_a_provider_replaces_every_level(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        bound = ruleset(tmp_path, skill, provider=JudgeProvider.GEMINI, model="bound-model")
        override = JudgeChoice(provider=JudgeProvider.CLAUDE_CLI)

        (binding,) = Bindings.from_rulesets([bound], project, override)

        assert binding.model == JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name=None)

    @pytest.mark.parametrize("model", ["gpt-6-luna", "gemini-3.1-pro-preview"])
    def test_model_other_than_claude_with_no_provider_named_is_an_error(
        self, tmp_path, make_skill, model
    ):
        skill = write_skill(tmp_path, make_skill().text)
        (binding,) = Bindings.from_rulesets([ruleset(tmp_path, skill, model=model)])

        with pytest.raises(ConfigError) as error:
            _ = binding.model

        assert str(error.value) == (
            f"model {model} needs a provider: set provider in the rule's binding, "
            "judge.provider in .codeguard/config.yaml (or CODEGUARD_JUDGE__PROVIDER), or "
            "judge.provider in its package's codeguard-package.yaml"
        )

    @pytest.mark.parametrize(
        ("provider", "model"),
        [
            (JudgeProvider.CLAUDE_CLI, "gpt-6-luna"),
            (JudgeProvider.CODEX_CLI, "claude-haiku-5-5"),
            (JudgeProvider.GEMINI, "claude-haiku-5-5"),
            (JudgeProvider.BEDROCK, "gemini-3.1-pro-preview"),
        ],
    )
    def test_model_the_provider_cant_run_is_an_error(self, tmp_path, make_skill, provider, model):
        skill = write_skill(tmp_path, make_skill().text)
        (binding,) = Bindings.from_rulesets(
            [ruleset(tmp_path, skill, provider=provider, model=model)]
        )

        with pytest.raises(ConfigError) as error:
            _ = binding.model

        assert str(error.value) == f"provider {provider} can't run model {model}"

    @pytest.mark.parametrize(
        ("provider", "model"),
        [
            (JudgeProvider.BEDROCK, "arn:aws:bedrock:us-west-2:1:application-inference-profile/x"),
            (JudgeProvider.BEDROCK, "gpt-6-luna"),
            (JudgeProvider.CODEX_CLI, "o9-mini"),
        ],
    )
    def test_model_of_no_family_the_provider_cant_run_passes(
        self, tmp_path, make_skill, provider, model
    ):
        skill = write_skill(tmp_path, make_skill().text)
        (binding,) = Bindings.from_rulesets(
            [ruleset(tmp_path, skill, provider=provider, model=model)]
        )

        assert binding.model == JudgeModel(provider=provider, name=model)

    def test_claude_model_with_no_provider_named_runs_on_the_claude_cli(self, tmp_path, make_skill):
        skill = write_skill(tmp_path, make_skill().text)

        (binding,) = Bindings.from_rulesets([ruleset(tmp_path, skill, model="claude-haiku-5-5")])

        assert binding.model == JudgeModel(
            provider=JudgeProvider.CLAUDE_CLI, name="claude-haiku-5-5"
        )


class TestSkill:
    def test_from_file_drops_the_frontmatter(self, tmp_path, make_skill):
        file = tmp_path / "SKILL.md"
        file.write_text(f"---\nname: {SKILL_NAME}\n---\n{make_skill().text}")

        skill = Skill.from_file(SKILL_NAME, file)

        assert skill == make_skill()
