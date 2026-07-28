#!/usr/bin/env python3
"""CLI-утилита для учёта личных расходов."""

import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime

CATEGORIES = ["еда", "транспорт", "жильё", "развлечения", "прочее"]
DATA_FILE = "expenses.json"

ONBOARDING = f"""Учёт расходов — простая CLI-утилита.

Команды:
  add      Добавить расход
  list     Показать список расходов
  summary  Сводка по категориям

Примеры:
  python expense_tracker.py add --amount 500 --category еда --date 2026-07-29 --note "бизнес-ланч"
  python expense_tracker.py list --from 2026-07-01 --to 2026-07-31
  python expense_tracker.py summary --category транспорт

Категории: {", ".join(CATEGORIES)}
Формат даты: YYYY-MM-DD
"""


def load_expenses():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_expenses(expenses):
    dir_name = os.path.dirname(os.path.abspath(DATA_FILE))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(expenses, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DATA_FILE)
    except BaseException:
        os.unlink(tmp_path)
        raise


def validate_amount(value):
    try:
        amount = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Неверная сумма: {value!r}. Ожидалось число.")
    if amount <= 0:
        raise argparse.ArgumentTypeError(f"Сумма должна быть положительной, получено: {amount}")
    return amount


def validate_category(value):
    if value not in CATEGORIES:
        raise argparse.ArgumentTypeError(
            f"Неверная категория: {value!r}. Допустимые: {", ".join(CATEGORIES)}"
        )
    return value


def validate_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Неверная дата: {value!r}. Ожидался формат YYYY-MM-DD."
        )
    return value


def cmd_add(args):
    expenses = load_expenses()
    record = {
        "id": str(uuid.uuid4()),
        "amount": args.amount,
        "category": args.category,
        "date": args.date,
        "note": args.note or "",
    }
    expenses.append(record)
    save_expenses(expenses)
    print(f"Добавлено: {record['amount']:.2f} ₽, {record['category']}, {record['date']} (id: {record['id'][:8]})")


def filter_expenses(expenses, date_from=None, date_to=None, category=None):
    result = expenses
    if date_from:
        result = [e for e in result if e["date"] >= date_from]
    if date_to:
        result = [e for e in result if e["date"] <= date_to]
    if category:
        result = [e for e in result if e["category"] == category]
    return result


def cmd_list(args):
    expenses = load_expenses()
    expenses = filter_expenses(expenses, args.date_from, args.date_to, args.category)
    if not expenses:
        print("Расходов нет")
        return
    expenses.sort(key=lambda e: e["date"], reverse=True)
    print(f"{'Дата':<12} {'Категория':<14} {'Сумма':>10}  Комментарий")
    print("-" * 60)
    for e in expenses:
        note = e.get("note", "")
        print(f"{e['date']:<12} {e['category']:<14} {e['amount']:>10.2f}  {note}")


def cmd_summary(args):
    expenses = load_expenses()
    expenses = filter_expenses(expenses, args.date_from, args.date_to, args.category)
    if not expenses:
        print("Расходов нет")
        return
    agg = {}
    for e in expenses:
        cat = e["category"]
        if cat not in agg:
            agg[cat] = {"total": 0.0, "count": 0}
        agg[cat]["total"] += e["amount"]
        agg[cat]["count"] += 1
    print(f"{'Категория':<14} {'Сумма':>10}  {'Записей':>7}")
    print("-" * 36)
    grand_total = 0.0
    grand_count = 0
    for cat in CATEGORIES:
        if cat in agg:
            print(f"{cat:<14} {agg[cat]['total']:>10.2f}  {agg[cat]['count']:>7}")
            grand_total += agg[cat]["total"]
            grand_count += agg[cat]["count"]
    print("-" * 36)
    print(f"{'Итого':<14} {grand_total:>10.2f}  {grand_count:>7}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="expense_tracker",
        description="CLI-утилита для учёта личных расходов",
    )
    subparsers = parser.add_subparsers(dest="command")

    # add
    p_add = subparsers.add_parser("add", help="Добавить расход")
    p_add.add_argument("--amount", required=True, type=validate_amount, help="Сумма (положительное число)")
    p_add.add_argument("--category", required=True, type=validate_category, help=f"Категория: {", ".join(CATEGORIES)}")
    p_add.add_argument("--date", required=True, type=validate_date, help="Дата (YYYY-MM-DD)")
    p_add.add_argument("--note", default="", help="Комментарий (необязательно)")

    # list
    p_list = subparsers.add_parser("list", help="Список расходов")
    p_list.add_argument("--from", dest="date_from", type=validate_date, help="Начальная дата (включительно)")
    p_list.add_argument("--to", dest="date_to", type=validate_date, help="Конечная дата (включительно)")
    p_list.add_argument("--category", type=validate_category, help="Фильтр по категории")

    # summary
    p_summary = subparsers.add_parser("summary", help="Сводка по категориям")
    p_summary.add_argument("--from", dest="date_from", type=validate_date, help="Начальная дата (включительно)")
    p_summary.add_argument("--to", dest="date_to", type=validate_date, help="Конечная дата (включительно)")
    p_summary.add_argument("--category", type=validate_category, help="Фильтр по категории")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        print(ONBOARDING)
        return

    commands = {
        "add": cmd_add,
        "list": cmd_list,
        "summary": cmd_summary,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
