# backend/api/models.py
import sqlite3
import os
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "webtalk.sqlite")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            verified INTEGER DEFAULT 1
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user TEXT NOT NULL,
            to_user TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending','accepted','rejected')) DEFAULT 'pending'
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS groups(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_by TEXT NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS group_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending','accepted','rejected')) DEFAULT 'pending'
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS group_members(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user TEXT NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT,        -- username for private chat
            group_id INTEGER,      -- group for group chat
            text TEXT NOT NULL,
            lamport INTEGER NOT NULL,
            ts INTEGER NOT NULL
        )""")
        conn.commit()

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def create_user(username, password):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users(username, password_hash, verified) VALUES(?,?,1)",
                    (username, generate_password_hash(password)))
        return cur.lastrowid

def validate_user(username, password):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        return row and check_password_hash(row["password_hash"], password)

def list_verified_users(exclude=None):
    with db() as conn:
        cur = conn.cursor()
        if exclude:
            cur.execute("SELECT username FROM users WHERE verified=1 AND username!=? ORDER BY username", (exclude,))
        else:
            cur.execute("SELECT username FROM users WHERE verified=1 ORDER BY username")
        return [r["username"] for r in cur.fetchall()]

def create_chat_request(from_user, to_user):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO chat_requests(from_user,to_user,status) VALUES(?,?, 'pending')",
                    (from_user, to_user))
        return cur.lastrowid

def set_chat_request_status(req_id, status):
    with db() as conn:
        conn.execute("UPDATE chat_requests SET status=? WHERE id=?", (status, req_id))

def list_incoming_requests(user):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM chat_requests WHERE to_user=? AND status='pending'", (user,))
        return [dict(r) for r in cur.fetchall()]

def is_chat_allowed(u1, u2):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT 1 FROM chat_requests
                       WHERE ((from_user=? AND to_user=?)
                              OR (from_user=? AND to_user=?))
                         AND status='accepted'""", (u1, u2, u2, u1))
        return cur.fetchone() is not None

def create_group(name, created_by):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO groups(name,created_by) VALUES(?,?)", (name, created_by))
        gid = cur.lastrowid
        cur.execute("INSERT INTO group_members(group_id,user) VALUES(?,?)", (gid, created_by))
        return gid

def list_groups():
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM groups ORDER BY name")]

def create_group_request(group_id, user):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO group_requests(group_id,user,status) VALUES(?,?,'pending')", (group_id, user))
        return cur.lastrowid

def list_group_requests_for_admin(admin_user):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT gr.id, gr.group_id, g.name as group_name, gr.user
                       FROM group_requests gr
                       JOIN groups g ON g.id=gr.group_id
                       WHERE g.created_by=? AND gr.status='pending'""", (admin_user,))
        return [dict(r) for r in cur.fetchall()]

def accept_group_request(req_id):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT group_id, user FROM group_requests WHERE id=?", (req_id,))
        r = cur.fetchone()
        if not r: return False
        cur.execute("UPDATE group_requests SET status='accepted' WHERE id=?", (req_id,))
        cur.execute("INSERT INTO group_members(group_id,user) VALUES(?,?)", (r["group_id"], r["user"]))
        return True

def is_member(group_id, user):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM group_members WHERE group_id=? AND user=?", (group_id, user))
        return cur.fetchone() is not None
def list_group_members(group_id: int) -> list[str]:
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user FROM group_members WHERE group_id=?", (group_id,))
        rows = cur.fetchall()
        return [r["user"] for r in rows]
