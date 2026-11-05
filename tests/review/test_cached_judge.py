import json

import pytest
from recording_judge import RecordingJudge
from spans import finished_span_attributes

from codeguard.review import CachedJudge, Judgement, JudgeRequest, ReportedDefault, Verdict

ORDER_SERVICE = (
    "from orders.pricing import DISCOUNT\n"
    "\n"
    "\n"
    "class OrderService:\n"
    "    def total(self, order):\n"
    "        return order.subtotal - DISCOUNT\n"
)
PRICING = "DISCOUNT = 5\n"
RECEIPT = "def receipt_line(order):\n    return f'{order.id}: {order.subtotal}'\n"


@pytest.fixture
def orders(repo):
    repo.write("orders/order_service.py", ORDER_SERVICE)
    repo.write("orders/pricing.py", PRICING)
    repo.write("orders/receipt.py", RECEIPT)
    return repo


def cached(repo, store, wrapped, **options) -> CachedJudge:
    return CachedJudge(wrapped=wrapped, store=store, root=repo.root, **options)


@pytest.fixture
def total_change(make_skill) -> JudgeRequest:
    return JudgeRequest(
        make_skill(),
        "orders/order_service.py",
        "     5\t    def total(self, order):\n     6\t        return order.subtotal - DISCOUNT\n",
    )


class TestCachedJudge:
    def test_uncached_request_goes_to_the_wrapped_judge(self, orders, store, total_change):
        wrapped = RecordingJudge()
        request = total_change

        cached(orders, store, wrapped).judge(request)

        assert wrapped.received == [request]

    def test_cached_judgement_is_returned_without_judging_again(
        self, orders, store, total_change, make_violation
    ):
        verdict = Verdict(
            reason="The code breaks the convention.",
            violations=(make_violation(file="orders/order_service.py"),),
        )
        wrapped = RecordingJudge(verdict, loaded_files=("orders/pricing.py",))
        judge = cached(orders, store, wrapped)
        request = total_change
        judge.judge(request)

        assert judge.judge(request) == Judgement(verdict, ("orders/pricing.py",))
        assert wrapped.received == [request]

    def test_cache_entry_that_is_not_a_stored_judgement_is_an_error(
        self, orders, store, total_change
    ):
        judge = cached(orders, store, RecordingJudge())
        request = total_change
        judge.judge(request)
        [key] = list(store)
        store[key] = "written by another version"

        with pytest.raises(TypeError, match=f"cache entry {key} is not a stored judgement"):
            judge.judge(request)

    def test_has_a_request_only_after_judging_it(self, orders, store, total_change):
        judge = cached(orders, store, RecordingJudge())
        request = total_change
        before = judge.has(request)

        judge.judge(request)

        assert (before, judge.has(request)) == (False, True)

    def test_changed_code_is_judged_again(self, orders, store, make_skill, total_change):
        wrapped = RecordingJudge()
        judge = cached(orders, store, wrapped)
        judge.judge(total_change)
        orders.write("orders/order_service.py", ORDER_SERVICE.replace("- DISCOUNT", "- 5"))
        changed = JudgeRequest(
            make_skill(),
            "orders/order_service.py",
            "     5\t    def total(self, order):\n     6\t        return order.subtotal - 5\n",
        )

        judge.judge(changed)

        assert wrapped.received == [total_change, changed]

    def test_edit_elsewhere_in_the_judged_file_is_judged_again(self, orders, store, total_change):
        wrapped = RecordingJudge()
        judge = cached(orders, store, wrapped)
        request = total_change
        judge.judge(request)
        orders.write("orders/order_service.py", f"import logging\n{ORDER_SERVICE}")

        judge.judge(request)

        assert wrapped.received == [request, request]

    def test_changed_file_the_judge_loaded_is_judged_again(self, orders, store, total_change):
        wrapped = RecordingJudge(loaded_files=("orders/pricing.py",))
        judge = cached(orders, store, wrapped)
        request = total_change
        judge.judge(request)
        orders.write("orders/pricing.py", "DISCOUNT = 10\n")

        judge.judge(request)

        assert wrapped.received == [request, request]

    def test_file_the_judge_loaded_that_was_missing_and_now_exists_is_judged_again(
        self, orders, store, total_change
    ):
        wrapped = RecordingJudge(loaded_files=("orders/discounts.py",))
        judge = cached(orders, store, wrapped)
        request = total_change
        judge.judge(request)
        orders.write("orders/discounts.py", "SEASONAL = 3\n")

        judge.judge(request)

        assert wrapped.received == [request, request]

    def test_changed_file_the_judge_did_not_load_keeps_the_verdict(
        self, orders, store, total_change
    ):
        wrapped = RecordingJudge(loaded_files=("orders/pricing.py",))
        judge = cached(orders, store, wrapped)
        request = total_change
        judge.judge(request)
        orders.write("orders/receipt.py", f"{RECEIPT}\n\ndef footer():\n    return 'Thanks'\n")

        judge.judge(request)

        assert wrapped.received == [request]

    def test_file_loaded_outside_the_repo_is_judged_every_time(self, orders, store, total_change):
        wrapped = RecordingJudge(loaded_files=("/etc/hostname",))
        judge = cached(orders, store, wrapped)
        request = total_change
        judge.judge(request)

        judge.judge(request)

        assert wrapped.received == [request, request]

    def test_changed_skill_text_is_judged_again(self, orders, store, make_skill, total_change):
        wrapped = RecordingJudge()
        judge = cached(orders, store, wrapped)
        judge.judge(total_change)
        revised = JudgeRequest(
            make_skill(text="# Revised\n"),
            "orders/order_service.py",
            total_change.changes,
        )

        judge.judge(revised)

        assert wrapped.received[-1] == revised

    def test_changed_wrapped_identity_is_judged_again(self, orders, store, total_change):
        request = total_change
        cached(orders, store, RecordingJudge(identity="first")).judge(request)
        second = RecordingJudge(identity="second")

        cached(orders, store, second).judge(request)

        assert second.received == [request]

    def test_changed_version_is_judged_again(self, orders, store, total_change):
        request = total_change
        cached(orders, store, RecordingJudge()).judge(request)
        wrapped = RecordingJudge()

        cached(orders, store, wrapped, version="another version").judge(request)

        assert wrapped.received == [request]

    def test_each_lookup_records_whether_the_cache_had_the_verdict(
        self, orders, store, total_change, make_violation, capfire
    ):
        wrapped = RecordingJudge(
            Verdict(reason="The code breaks the convention.", violations=(make_violation(),)),
            loaded_files=("orders/pricing.py",),
        )
        judge = cached(orders, store, wrapped)
        request = total_change

        judge.judge(request)
        judge.judge(request)

        lookup = {
            "rule": request.skill.name,
            "file": request.file,
            "violations": 1,
            "changed_files": "[]",
            "loaded_files": '["orders/pricing.py"]',
        }
        assert finished_span_attributes(capfire, "judge {rule} on {file}") == [
            {**lookup, "cache_hit": False},
            {**lookup, "cache_hit": True},
        ]

    def test_lookup_records_the_loaded_files_that_changed(
        self, orders, store, total_change, capfire
    ):
        wrapped = RecordingJudge(loaded_files=("orders/pricing.py", "orders/receipt.py"))
        judge = cached(orders, store, wrapped)
        judge.judge(total_change)
        orders.write("orders/pricing.py", "DISCOUNT = 10\n")

        judge.judge(total_change)

        [_, rejudged] = finished_span_attributes(capfire, "judge {rule} on {file}")
        assert (rejudged["cache_hit"], json.loads(rejudged["changed_files"])) == (
            False,
            ["orders/pricing.py"],
        )


class TestCachedJudgeOnTheCliDefault:
    def test_first_request_is_judged_though_a_verdict_is_cached(self, orders, store, total_change):
        cached(orders, store, RecordingJudge(model="model-a"), default=ReportedDefault()).judge(
            total_change
        )
        wrapped = RecordingJudge(model="model-a")

        cached(orders, store, wrapped, default=ReportedDefault()).judge(total_change)

        assert wrapped.received == [total_change]

    def test_later_requests_reuse_verdicts_of_the_reported_default(
        self, orders, store, total_change, make_skill
    ):
        default = ReportedDefault()
        wrapped = RecordingJudge(model="model-a")
        judge = cached(orders, store, wrapped, default=default)
        other = JudgeRequest(
            make_skill(), "orders/receipt.py", "     1\tdef receipt_line(order):\n"
        )
        judge.judge(total_change)
        judge.judge(other)

        judge.judge(total_change)

        assert wrapped.received == [total_change, other]

    def test_verdict_of_an_earlier_default_is_judged_again(self, orders, store, total_change):
        old_default = ReportedDefault()
        cached(orders, store, RecordingJudge(model="model-a"), default=old_default).judge(
            total_change
        )
        new_default = ReportedDefault(known=True, model="model-b")
        wrapped = RecordingJudge(model="model-b")

        cached(orders, store, wrapped, default=new_default).judge(total_change)

        assert wrapped.received == [total_change]

    def test_cli_reporting_no_model_is_never_cached(self, orders, store, total_change):
        default = ReportedDefault()
        wrapped = RecordingJudge()
        judge = cached(orders, store, wrapped, default=default)
        judge.judge(total_change)

        judge.judge(total_change)

        assert wrapped.received == [total_change, total_change]
        assert not judge.has(total_change)
