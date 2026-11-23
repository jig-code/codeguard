from pathlib import Path

from codeguard.cli.eval_command import EvalCommand
from codeguard.config import JudgeChoice, JudgeProvider
from codeguard.repository import WorkingTree


class TestEvalCommand:
    def test_without_a_provider_overrides_nothing(self):
        assert EvalCommand().judge_override == JudgeChoice()

    def test_provider_and_model_override_every_rule_s_judge(self):
        command = EvalCommand(provider=JudgeProvider.GEMINI, model="gemini-judge-test")

        assert command.judge_override == JudgeChoice.of_provider(
            JudgeProvider.GEMINI, "gemini-judge-test"
        )

    def test_package_is_the_working_tree(self, tmp_path):
        command = EvalCommand(package=tmp_path / "rules")

        assert command.working_tree(Path("/")) == WorkingTree.at(tmp_path / "rules")
