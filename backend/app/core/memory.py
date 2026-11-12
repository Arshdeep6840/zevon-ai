"""SQLite storage: chat history, long-term memory, instructions, approvals, audit log."""
import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, session TEXT, role TEXT, content TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, text TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS instructions(id INTEGER PRIMARY KEY, name TEXT, kind TEXT, schedule TEXT, text TEXT, enabled INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY, tool TEXT, args TEXT, session TEXT, status TEXT, result TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, ts REAL, actor TEXT, action TEXT, detail TEXT, outcome TEXT);
"""


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript(SCHEMA)

    def _exec(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur

    def _rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    # chat
    def add_message(self, session, role, content):
        self._exec("INSERT INTO messages(session,role,content,ts) VALUES(?,?,?,?)", (session, role, content, time.time()))

    def history(self, session, limit=20):
        rows = self._rows("SELECT role,content FROM messages WHERE session=? ORDER BY id DESC LIMIT ?", (session, limit))
        return list(reversed(rows))

    # long-term memory
    def remember(self, text):
        return self._exec("INSERT INTO memories(text,ts) VALUES(?,?)", (text, time.time())).lastrowid

    def memories(self, query="", limit=20):
        if query:
            return self._rows("SELECT * FROM memories WHERE text LIKE ? ORDER BY id DESC LIMIT ?", (f"%{query}%", limit))
        return self._rows("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,))

    # instructions: permanent | scheduled (cron) | conditional
    def add_instruction(self, name, kind, text, schedule=""):
        return self._exec("INSERT INTO instructions(name,kind,schedule,text) VALUES(?,?,?,?)", (name, kind, schedule, text)).lastrowid

    def instructions(self, kind=None, enabled_only=False):
        sql, args = "SELECT * FROM instructions WHERE 1=1", []
        if kind:
            sql += " AND kind=?"; args.append(kind)
        if enabled_only:
            sql += " AND enabled=1"
        return self._rows(sql, args)

    def set_instruction_enabled(self, iid, enabled):
        self._exec("UPDATE instructions SET enabled=? WHERE id=?", (int(enabled), iid))

    def delete_instruction(self, iid):
        self._exec("DELETE FROM instructions WHERE id=?", (iid,))

    # approvals
    def add_approval(self, tool, args, session):
        return self._exec("INSERT INTO approvals(tool,args,session,status,ts) VALUES(?,?,?,?,?)",
                          (tool, json.dumps(args), session, "pending", time.time())).lastrowid

    def get_approval(self, aid):
        rows = self._rows("SELECT * FROM approvals WHERE id=?", (aid,))
        if rows:
            rows[0]["args"] = json.loads(rows[0]["args"])
        return rows[0] if rows else None

    def approvals(self, status="pending"):
        rows = self._rows("SELECT * FROM approvals WHERE status=? ORDER BY id DESC", (status,))
        for r in rows:
            r["args"] = json.loads(r["args"])
        return rows

    def resolve_approval(self, aid, status, result=""):
        self._exec("UPDATE approvals SET status=?, result=? WHERE id=?", (status, result, aid))

    # audit
    def audit(self, actor, action, detail="", outcome="ok"):
        self._exec("INSERT INTO audit(ts,actor,action,detail,outcome) VALUES(?,?,?,?,?)",
                   (time.time(), actor, action, str(detail)[:2000], outcome))

    def audit_log(self, limit=100):
        return self._rows("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))
