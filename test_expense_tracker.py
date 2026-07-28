"""Тесты для expense_tracker.py."""

import json
import os
import subprocess
import sys
import tempfile

import pytest

import expense_tracker


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    data_file = str(tmp_path / "expenses.json")
    monkeypatch.setattr(expense_tracker, "DATA_FILE", data_file)
    return data_file


class TestValidation:
    def test_negative_amount(self):
        with pytest.raises(SystemExit):
            expense_tracker.main(["add", "--amount", "-5", "--category", "еда", "--date", "2026-07-29"])

    def test_zero_amount(self):
        with pytest.raises(SystemExit):
            expense_tracker.main(["add", "--amount", "0", "--category", "еда", "--date", "2026-07-29"])

    def test_non_numeric_amount(self):
        with pytest.raises(SystemExit):
            expense_tracker.main(["add", "--amount", "abc", "--category", "еда", "--date", "2026-07-29"])

    def test_invalid_category(self):
        with pytest.raises(SystemExit):
            expense_tracker.main(["add", "--amount", "100", "--category", "одежда", "--date", "2026-07-29"])

    def test_invalid_date_format(self):
        with pytest.raises(SystemExit):
            expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "29.07.2026"])

    def test_nonexistent_date(self):
        with pytest.raises(SystemExit):
            expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-02-30"])


class TestAdd:
    def test_add_creates_record(self, isolated_data):
        expense_tracker.main(["add", "--amount", "500", "--category", "еда", "--date", "2026-07-29", "--note", "обед"])
        with open(isolated_data, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["amount"] == 500.0
        assert data[0]["category"] == "еда"
        assert data[0]["date"] == "2026-07-29"
        assert data[0]["note"] == "обед"
        assert "id" in data[0]

    def test_add_without_note(self, isolated_data):
        expense_tracker.main(["add", "--amount", "200", "--category", "транспорт", "--date", "2026-07-28"])
        with open(isolated_data, encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["note"] == ""

    def test_add_multiple(self, isolated_data):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "200", "--category", "транспорт", "--date", "2026-07-02"])
        with open(isolated_data, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2


class TestList:
    def test_list_empty(self, isolated_data, capsys):
        expense_tracker.main(["list"])
        assert "Расходов нет" in capsys.readouterr().out

    def test_list_sorted_by_date_desc(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "200", "--category", "транспорт", "--date", "2026-07-03"])
        expense_tracker.main(["add", "--amount", "300", "--category", "жильё", "--date", "2026-07-02"])
        capsys.readouterr()
        expense_tracker.main(["list"])
        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if l and not l.startswith("-") and "Дата" not in l]
        assert "2026-07-03" in lines[0]
        assert "2026-07-02" in lines[1]
        assert "2026-07-01" in lines[2]

    def test_list_filter_from(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "200", "--category", "еда", "--date", "2026-07-15"])
        capsys.readouterr()
        expense_tracker.main(["list", "--from", "2026-07-10"])
        out = capsys.readouterr().out
        assert "2026-07-15" in out
        assert "2026-07-01" not in out

    def test_list_filter_to(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "200", "--category", "еда", "--date", "2026-07-15"])
        capsys.readouterr()
        expense_tracker.main(["list", "--to", "2026-07-10"])
        out = capsys.readouterr().out
        assert "2026-07-01" in out
        assert "2026-07-15" not in out

    def test_list_filter_category(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "200", "--category", "транспорт", "--date", "2026-07-01"])
        capsys.readouterr()
        expense_tracker.main(["list", "--category", "еда"])
        out = capsys.readouterr().out
        assert "еда" in out
        assert "транспорт" not in out


class TestSummary:
    def test_summary_empty(self, isolated_data, capsys):
        expense_tracker.main(["summary"])
        assert "Расходов нет" in capsys.readouterr().out

    def test_summary_aggregation(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "250", "--category", "еда", "--date", "2026-07-02"])
        expense_tracker.main(["add", "--amount", "500", "--category", "транспорт", "--date", "2026-07-03"])
        expense_tracker.main(["summary"])
        out = capsys.readouterr().out
        assert "350.00" in out  # еда total
        assert "500.00" in out  # транспорт total
        assert "850.00" in out  # итого

    def test_summary_hides_empty_categories(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["summary"])
        out = capsys.readouterr().out
        assert "еда" in out
        assert "транспорт" not in out
        assert "жильё" not in out

    def test_summary_filter_category(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "500", "--category", "транспорт", "--date", "2026-07-02"])
        capsys.readouterr()
        expense_tracker.main(["summary", "--category", "еда"])
        out = capsys.readouterr().out
        assert "еда" in out
        assert "транспорт" not in out

    def test_summary_filter_dates(self, isolated_data, capsys):
        expense_tracker.main(["add", "--amount", "100", "--category", "еда", "--date", "2026-07-01"])
        expense_tracker.main(["add", "--amount", "200", "--category", "еда", "--date", "2026-08-01"])
        expense_tracker.main(["summary", "--from", "2026-07-15", "--to", "2026-08-15"])
        out = capsys.readouterr().out
        assert "200.00" in out
        assert "Итого" in out


class TestOnboarding:
    def test_no_subcommand_shows_onboarding(self, capsys):
        expense_tracker.main([])
        out = capsys.readouterr().out
        assert "Команды:" in out
        assert "Категории:" in out
        assert "YYYY-MM-DD" in out
