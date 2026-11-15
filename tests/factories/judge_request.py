import factory

from codeguard.review import JudgeRequest
from factories.judge_rule import MakeJudgeRule


class MakeJudgeRequest(factory.Factory):
    class Meta:
        model = JudgeRequest

    judge_rule = factory.SubFactory(MakeJudgeRule)
    file = "a.py"
    changes = "+     1\tprint(1)\n"
