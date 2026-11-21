import io

from codeguard.review import JudgePlan, PlannedCall


class TestJudgePlan:
    def test_reports_every_call_by_rule_by_file_and_for_each_file(self):
        plan = JudgePlan(
            calls=(
                PlannedCall(rule="no-dead-code", file="a.py", cached=False, triggered=True),
                PlannedCall(rule="no-dead-code", file="b.py", cached=True, triggered=True),
                PlannedCall(rule="enum-usage", file="a.py", cached=False, triggered=False),
                PlannedCall(rule="enum-usage", file="b.py", cached=True, triggered=True),
            )
        )
        out = io.StringIO()

        plan.write(out)

        assert out.getvalue() == (
            "Judge calls: 3 (2 cached, 1 new), 1 skipped by triggers\n"
            "\n"
            "By rule:\n"
            "     new  cached  skipped  rule\n"
            "       1       1        0  no-dead-code\n"
            "       0       1        1  enum-usage\n"
            "\n"
            "By file:\n"
            "     new  cached  skipped  file\n"
            "       0       2        0  b.py\n"
            "       1       0        1  a.py\n"
            "\n"
            "Calls by file:\n"
            "a.py\n"
            "  new      no-dead-code\n"
            "  skipped  enum-usage\n"
            "b.py\n"
            "  cached   enum-usage\n"
            "  cached   no-dead-code\n"
        )

    def test_plan_without_calls_reports_only_the_total(self):
        out = io.StringIO()

        JudgePlan(calls=()).write(out)

        assert out.getvalue() == "Judge calls: 0 (0 cached, 0 new), 0 skipped by triggers\n"
