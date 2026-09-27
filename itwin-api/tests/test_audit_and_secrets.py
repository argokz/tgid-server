"""audit_log (changed_at без таймзоны), запись -save_po из out_file sety, пароли вне логов."""

import datetime
import subprocess
import uuid

import pytest

import worker
from audit import build_audit_insert

AUDIT_COLS = {
    "log_id", "comment", "operation", "table_name", "record_id", "node_id", "old_data",
    "new_data", "changed_at", "changed_by", "change_group_id", "is_rolled_back",
}


def _audit(available=AUDIT_COLS, **kw):
    params = dict(
        changed_by="ivanov", operation="RUN_SETY", table_name="calculation", record_id=5,
        old_data=None, new_data={"params": "-Tn -25"}, change_group_id=str(uuid.uuid4()),
    )
    params.update(kw)
    return build_audit_insert(available, **params)


def test_audit_changed_at_is_server_now_not_a_parameter():
    sql, args = _audit()
    # changed_at — timestamp without time zone: aware-datetime параметром asyncpg не кодирует
    assert '"changed_at"' in sql and "now()" in sql
    assert not any(isinstance(a, datetime.datetime) for a in args)
    assert sql.count("$") == len(args)
    columns = [c.strip('"') for c in sql.split("(", 1)[1].split(")", 1)[0].split(", ")]
    assert isinstance(args[columns.index("change_group_id")], uuid.UUID)


def test_audit_legacy_column_names_and_no_columns():
    sql, args = _audit({"tablename", "recordid", "operation"})
    assert '"tablename"' in sql and '"recordid"' in sql and "changed_at" not in sql
    assert args == ["RUN_SETY", "calculation", 5]
    assert _audit({"changed_at"}) is None


def _write_po_files(tmp_path, sql_text, encoding=None):
    enc = encoding or worker._sety_text_encoding()
    sql_file = tmp_path / "tmp_po.sql"
    sql_file.write_bytes(sql_text.encode(enc))
    out_file = tmp_path / "out.txt"
    out_file.write_bytes((str(sql_file) + "\n").encode(enc))
    return out_file, sql_file


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 3

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql):
        if self.conn.fail:
            raise RuntimeError("relation does not exist")
        self.conn.executed.append(sql)


class _FakeConn:
    def __init__(self, fail=False):
        self.fail = fail
        self.executed, self.committed, self.rolled_back, self.closed = [], False, False, False

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


PO_SQL = "\nUPDATE generalizedconsumers\nset\n    otoplz = _t.q\nfrom nodes n where n.externalnodename = 'ТК-1'\n"


def test_save_po_sql_is_executed_in_one_transaction(tmp_path, monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(worker, "_po_db_connect", lambda: conn)
    out_file, sql_file = _write_po_files(tmp_path, PO_SQL, encoding="cp1251")
    msg = worker._apply_out_file_sql(str(out_file))
    assert "обновлено строк 3" in msg
    assert conn.executed == [PO_SQL.strip()] and "ТК-1" in conn.executed[0]
    assert conn.committed and not conn.rolled_back and conn.closed
    assert not sql_file.exists()


def test_save_po_error_rolls_back_and_goes_to_protocol(tmp_path, monkeypatch):
    conn = _FakeConn(fail=True)
    monkeypatch.setattr(worker, "_po_db_connect", lambda: conn)
    out_file, sql_file = _write_po_files(tmp_path, PO_SQL)

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="Расчет закончен\n", stderr="")

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    run = worker._run_one(["ww.py", "-out_file", str(out_file)], "t", "1")
    assert run["status"] == "error"
    assert "обобщённые потребители" in run["error"] and "relation does not exist" in run["output"]
    assert conn.rolled_back and not conn.committed and conn.closed
    assert not sql_file.exists() and not out_file.exists()


def test_save_po_rejects_unexpected_sql(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "_po_db_connect", lambda: pytest.fail("не должно подключаться"))
    out_file, sql_file = _write_po_files(tmp_path, "DROP TABLE nodes")
    with pytest.raises(RuntimeError):
        worker._apply_out_file_sql(str(out_file))
    assert not sql_file.exists()


def test_no_out_file_means_nothing_to_write(tmp_path):
    assert worker._apply_out_file_sql(str(tmp_path / "missing.txt")) is None


def test_worker_masks_db_password(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "S3cr-et!")
    cmd = worker._sety_base_cmd("out.txt", True)
    assert "S3cr-et!" in cmd  # sety нужен пароль в аргументах...
    assert "S3cr-et!" not in worker._masked(cmd)  # ...но в лог он не попадает
    assert worker._redact("login failed S3cr-et!") == "login failed ***"


def test_connect_logs_users_config_without_password():
    from database import connect

    safe = connect.safe_db_config({"user": "u", "password": "p@ss", "host": "h"})
    assert safe == {"user": "u", "password": "***", "host": "h"}
    password = connect.USERS_DB_CONFIG.get("password")
    if password:
        assert password not in str(connect.USERS_DB_URL)
    assert connect.users_engine.echo is False
