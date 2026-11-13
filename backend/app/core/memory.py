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
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, ts REAL, title TEXT, body TEXT, read INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS seen(key TEXT PRIMARY KEY, ts REAL);
CREATE TABLE IF NOT EXISTS push_subs(endpoint TEXT PRIMARY KEY, sub TEXT);
CREATE TABLE IF NOT EXISTS session_summaries(session TEXT PRIMARY KEY, summary TEXT, upto_id INTEGER);
CREATE TABLE IF NOT EXISTS tool_policies(tool TEXT PRIMARY KEY, decision TEXT);
CREATE TABLE IF NOT EXISTS fcm_tokens(token TEXT PRIMARY KEY);
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

    # notifications / triggers / push
    def add_notification(self, title, body):
        return self._exec("INSERT INTO notifications(ts,title,body) VALUES(?,?,?)", (time.time(), title, str(body)[:2000])).lastrowid

    def notifications(self, unread_only=False, limit=50):
        sql = "SELECT * FROM notifications" + (" WHERE read=0" if unread_only else "") + " ORDER BY id DESC LIMIT ?"
        return self._rows(sql, (limit,))

    def mark_notifications_read(self):
        self._exec("UPDATE notifications SET read=1")

    def is_seen(self, key):
        return bool(self._rows("SELECT 1 FROM seen WHERE key=?", (key,)))

    def mark_seen(self, key):
        self._exec("INSERT OR IGNORE INTO seen(key,ts) VALUES(?,?)", (key, time.time()))

    def seen_count(self, prefix):
        return self._rows("SELECT COUNT(*) AS n FROM seen WHERE key LIKE ?", (prefix + "%",))[0]["n"]

    def add_push_sub(self, endpoint, sub: dict):
        self._exec("INSERT OR REPLACE INTO push_subs(endpoint,sub) VALUES(?,?)", (endpoint, json.dumps(sub)))

    def push_subs(self):
        return [json.loads(r["sub"]) for r in self._rows("SELECT sub FROM push_subs")]

    def remove_push_sub(self, endpoint):
        self._exec("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))

    # sessions / summaries
    def history_rows(self, session):
        return self._rows("SELECT id,role,content FROM messages WHERE session=? ORDER BY id", (session,))

    def sessions(self):
        rows = self._rows("SELECT session, COUNT(*) AS messages, MAX(ts) AS last_ts FROM messages GROUP BY session ORDER BY last_ts DESC")
        for r in rows:
            first = self._rows("SELECT content FROM messages WHERE session=? AND role='user' ORDER BY id LIMIT 1", (r["session"],))
            r["title"] = (first[0]["content"][:60] if first else r["session"])
            r["kind"] = "automation" if r["session"].startswith(("scheduled-", "rule-")) else "chat"
        return rows

    def delete_session(self, session):
        self._exec("DELETE FROM messages WHERE session=?", (session,))
        self._exec("DELETE FROM session_summaries WHERE session=?", (session,))

    def get_summary(self, session):
        r = self._rows("SELECT summary,upto_id FROM session_summaries WHERE session=?", (session,))
        return (r[0]["summary"], r[0]["upto_id"]) if r else None

    def set_summary(self, session, summary, upto_id):
        self._exec("INSERT OR REPLACE INTO session_summaries(session,summary,upto_id) VALUES(?,?,?)", (session, summary, upto_id))

    # memories CRUD
    def get_memory(self, mid):
        r = self._rows("SELECT * FROM memories WHERE id=?", (mid,))
        return r[0] if r else None

    def update_memory(self, mid, text):
        self._exec("UPDATE memories SET text=? WHERE id=?", (text, mid))

    def delete_memory(self, mid):
        self._exec("DELETE FROM memories WHERE id=?", (mid,))

    # per-tool permission overrides
    def tool_policies(self):
        return {r["tool"]: r["decision"] for r in self._rows("SELECT tool,decision FROM tool_policies")}

    def set_tool_policy(self, tool, decision):
        self._exec("INSERT OR REPLACE INTO tool_policies(tool,decision) VALUES(?,?)", (tool, decision))

    def clear_tool_policy(self, tool):
        self._exec("DELETE FROM tool_policies WHERE tool=?", (tool,))

    # FCM tokens (Android push)
    def add_fcm_token(self, token):
        self._exec("INSERT OR IGNORE INTO fcm_tokens(token) VALUES(?)", (token,))

    def fcm_tokens(self):
        return [r["token"] for r in self._rows("SELECT token FROM fcm_tokens")]

    def remove_fcm_token(self, token):
        self._exec("DELETE FROM fcm_tokens WHERE token=?", (token,))
