"""Имена операций журналов помещаются в колонки: audit_log.operation — varchar(10) в базах городов (длиннее — запись
молча уходит только в лог приложения), журнал действий пользователей — action[:20] (длиннее — обрезается)."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_MAX, ACTIVITY_MAX = 10, 20
HELPERS = {"write_audit_log", "audit", "_audit", "_audit_users"}


def _const(v):
    return v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) and v.value.isupper() else None


def _activity_helper(tree) -> bool:
    """_audit этого файла пишет в журнал действий пользователей (activity.write), а не в audit_log."""
    for fn in ast.walk(tree):
        if isinstance(fn, ast.AsyncFunctionDef | ast.FunctionDef) and fn.name == "_audit":
            return "activity.write" in ast.unparse(fn)
    return False


def _names():
    """(файл, строка, имя операции, журнал) для вызовов помощников аудита с именем-константой."""
    for p in [*ROOT.glob("routers/*.py"), *ROOT.glob("database/*.py"), *ROOT.glob("ai/*.py"), ROOT / "audit.py"]:
        tree = ast.parse(p.read_text(encoding="utf-8-sig"))  # у части файлов — BOM
        activity = _activity_helper(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name not in HELPERS and name != "write":  # write — _audit_writer привязок и групповых установщиков;
                continue                                  # _run(operation=…) — журнал отмены, varchar(32)
            values = [_const(k.value) for k in node.keywords if k.arg == "operation"]
            if name in HELPERS:
                values += [_const(a) for a in node.args[:3]]
            kind = "activity" if name == "_audit" and activity else "audit_log"
            for v in filter(None, values):
                yield p.name, node.lineno, v, kind


def test_audit_log_operations_fit_varchar10():
    bad = [n for n in _names() if n[3] == "audit_log" and len(n[2]) > AUDIT_MAX]
    assert not bad, bad


def test_activity_actions_fit():
    bad = [n for n in _names() if n[3] == "activity" and len(n[2]) > ACTIVITY_MAX]
    assert not bad, bad


def test_module_operation_constants():
    from database import defect_binding

    assert len(defect_binding.OPERATION) <= AUDIT_MAX
