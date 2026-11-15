import factory

from codeguard.review import JudgeRequest
from factories.judge_rule import MakeJudgeRule


class MakeJudgeRequest(factory.Factory):
    class Meta:
        model = JudgeRequest

    judge_rule = factory.SubFactory(MakeJudgeRule)
    file = "a.py"
    changes = "--- /dev/null\n+++ b/a.py\n@@ -0,0 +1 @@\n+print(1)\n"
