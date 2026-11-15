import factory

from codeguard.review import JudgeRequest
from factories.skill import MakeSkill


class MakeJudgeRequest(factory.Factory):
    class Meta:
        model = JudgeRequest

    skill = factory.SubFactory(MakeSkill)
    file = "a.py"
    changes = "--- /dev/null\n+++ b/a.py\n@@ -0,0 +1 @@\n+print(1)\n"
