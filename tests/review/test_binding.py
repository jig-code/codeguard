from codeguard.config import JudgeChoice, JudgeProvider, RuleOverride, RulesetConfig
from codeguard.review import Binding, Bindings, Severity, Skill

SKILL_NAME = "responsibility-placement"


def write_skill(tmp_path, text: str):
    (tmp_path / SKILL_NAME).mkdir()
    (tmp_path / SKILL_NAME / "SKILL.md").write_text(text)
    return tmp_path / SKILL_NAME


class TestBinding:
    def test_files_matching_its_paths_are_kept(self, make_binding):
        binding = make_binding(paths=("app/**/*.py",))

        files = binding.files(["app/a.py", "app/models/b.py", "scripts/c.py"])

        assert files == ["app/a.py", "app/models/b.py"]

    def test_files_matching_its_exclude_paths_are_left_out(self, make_binding):
        binding = make_binding(paths=("**/*.py",), exclude_paths=("**/test_*.py",))

        files = binding.files(["app/a.py", "app/test_a.py", "app/b.rb"])

        assert files == ["app/a.py"]

    def test_from_config_has_its_exclude_paths(
        self, tmp_path, make_binding, make_binding_config, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        config = make_binding_config(skill=skill, exclude_paths=("tests/**",))

        binding = Binding.from_config(SKILL_NAME, config, JudgeChoice())

        assert binding == make_binding(exclude_paths=("tests/**",))

    def test_preset_binding_matches_every_file(self, make_binding):
        binding = make_binding()

        files = binding.files(["a.py", "app/b.rb"])

        assert files == ["a.py", "app/b.rb"]

    def test_from_config_builds_its_skill(
        self, tmp_path, make_binding, make_binding_config, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        config = make_binding_config(skill=skill, severity=Severity.WARNING)

        binding = Binding.from_config(SKILL_NAME, config, JudgeChoice())

        assert binding == make_binding(severity=Severity.WARNING)

    def test_from_config_has_its_judge(
        self, tmp_path, make_binding, make_binding_config, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        judge = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="gpt-6-luna")

        binding = Binding.from_config(SKILL_NAME, make_binding_config(skill=skill), judge)

        assert binding == make_binding(judge=judge)


class TestBindings:
    def test_from_rulesets_builds_each_binding(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)

        bindings = Bindings.from_rulesets([make_ruleset(binding__skill=skill)])

        assert bindings == (make_binding(),)

    def test_packaged_binding_is_named_by_its_ruleset(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, name="example/python")]
        )

        assert bindings == (make_binding(rule=f"example/python/{SKILL_NAME}"),)

    def test_excluded_binding_is_dropped(self, tmp_path, make_ruleset, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        selection = RulesetConfig(exclude=(SKILL_NAME,))

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, name="example/python", selection=selection)]
        )

        assert bindings == ()

    def test_binding_left_out_of_include_is_dropped(self, tmp_path, make_ruleset, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        selection = RulesetConfig(include=("another-rule",))

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, name="example/python", selection=selection)]
        )

        assert bindings == ()

    def test_included_binding_is_kept(self, tmp_path, make_binding, make_ruleset, make_skill):
        skill = write_skill(tmp_path, make_skill().text)
        selection = RulesetConfig(include=(SKILL_NAME,))

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, name="example/python", selection=selection)]
        )

        assert bindings == (make_binding(rule=f"example/python/{SKILL_NAME}"),)

    def test_override_replaces_the_binding_fields(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        override = RuleOverride(paths=("app/**",), severity=Severity.WARNING)
        selection = RulesetConfig(rules={SKILL_NAME: override})

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, name="example/python", selection=selection)]
        )

        assert bindings == (
            make_binding(
                rule=f"example/python/{SKILL_NAME}",
                paths=("app/**",),
                severity=Severity.WARNING,
            ),
        )

    def test_override_replaces_the_excluded_paths(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        selection = RulesetConfig(rules={SKILL_NAME: RuleOverride(exclude_paths=())})
        ruleset = make_ruleset(
            binding__skill=skill, binding__exclude_paths=("tests/**",), selection=selection
        )

        assert Bindings.from_rulesets([ruleset]) == (make_binding(),)


class TestBindingsJudge:
    def test_package_default_judges_its_rules(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(provider=JudgeProvider.BEDROCK, model="package-model")

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, package_judge=package)]
        )

        assert bindings == (make_binding(judge=package),)

    def test_project_default_wins_over_the_package_default(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, package_judge=package)], project
        )

        assert bindings == (make_binding(judge=project),)

    def test_binding_wins_over_the_project_default(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(
            binding__skill=skill,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="bound-model",
        )

        bindings = Bindings.from_rulesets([ruleset], project)

        assert bindings == (
            make_binding(judge=JudgeChoice(provider=JudgeProvider.GEMINI, model="bound-model")),
        )

    def test_provider_and_model_each_come_from_the_first_level_naming_it(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(model="package-model")
        project = JudgeChoice(provider=JudgeProvider.BEDROCK)
        ruleset = make_ruleset(
            binding__skill=skill, binding__model="bound-model", package_judge=package
        )

        bindings = Bindings.from_rulesets([ruleset], project)

        assert bindings == (
            make_binding(judge=JudgeChoice(provider=JudgeProvider.BEDROCK, model="bound-model")),
        )

    def test_project_model_runs_on_the_package_provider(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        package = JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="package-model")
        project = JudgeChoice(model="project-model")

        bindings = Bindings.from_rulesets(
            [make_ruleset(binding__skill=skill, package_judge=package)], project
        )

        assert bindings == (
            make_binding(
                judge=JudgeChoice(provider=JudgeProvider.CODEX_CLI, model="project-model")
            ),
        )

    def test_override_naming_a_provider_replaces_every_level(
        self, tmp_path, make_binding, make_ruleset, make_skill
    ):
        skill = write_skill(tmp_path, make_skill().text)
        project = JudgeChoice(provider=JudgeProvider.BEDROCK, model="project-model")
        ruleset = make_ruleset(
            binding__skill=skill,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="bound-model",
        )
        override = JudgeChoice(provider=JudgeProvider.CLAUDE_CLI)

        bindings = Bindings.from_rulesets([ruleset], project, override)

        assert bindings == (make_binding(judge=override),)


class TestSkill:
    def test_from_file_drops_the_frontmatter(self, tmp_path, make_skill):
        file = tmp_path / "SKILL.md"
        file.write_text(f"---\nname: {SKILL_NAME}\n---\n{make_skill().text}")

        skill = Skill.from_file(SKILL_NAME, file)

        assert skill == make_skill()
