from shop.customers import legacy_export


def test_legacy_export_prints_nothing_for_no_customers(capsys):
    legacy_export([])
    assert capsys.readouterr().out == ""
