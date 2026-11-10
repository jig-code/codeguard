import factory

from codeguard.review import JudgeRequest
from factories.skill import MakeSkill


class MakeJudgeRequest(factory.Factory):
    class Meta:
        model = JudgeRequest

    skill = factory.SubFactory(MakeSkill)
    file = "a.py"
    changes = (
        "diff --git a/a.py b/a.py\n"
        "new file mode 100644\n"
        "index 0000000..b917a72\n"
        "--- /dev/null\n"
        "+++ b/a.py\n"
        "@@ -0,0 +1 @@\n"
        "+print(1)\n"
    )
