from collections import defaultdict
from pathlib import Path

SKILL_EVALS = Path(__file__).parent.parent / "evals" / "writing-rules"


class TestSkillEvals:
    def test_graders_with_the_same_name_are_identical(self):
        graders = defaultdict(set)
        for grader in SKILL_EVALS.glob("*/graders/*.md"):
            graders[grader.name].add(grader.read_text())

        differing = sorted(name for name, texts in graders.items() if len(texts) > 1)

        assert differing == []
