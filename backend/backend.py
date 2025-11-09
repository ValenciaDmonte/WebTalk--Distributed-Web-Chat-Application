import socket, threading, json, sqlite3, os

os.makedirs("database", exist_ok=True)
DB = "database/backup.sqlite"
conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT,
    sender TEXT,
    recipient TEXT,
    groupname TEXT,
    text TEXT,
    lamport INTEGER,
    ts INTEGER
)""")
conn.commit()

def handle(conn_sock):
    try:
        while True:
            data = conn_sock.recv(4096)
            if not data: break
            msg = json.loads(data.decode())
            kind = msg.get("kind")
            if kind == "private":
                cur.execute(
                    "INSERT INTO messages(kind,sender,recipient,text,lamport,ts) VALUES(?,?,?,?,?,?)",
                    ("private", msg["from"], msg.get("to"), msg["message"], msg["clock"], msg["ts"])
                )
            elif kind == "group":
                cur.execute(
                    "INSERT INTO messages(kind,sender,groupname,text,lamport,ts) VALUES(?,?,?,?,?,?)",
                    ("group", msg["from"], msg.get("group"), msg["message"], msg["clock"], msg["ts"])
                )
            conn.commit()
            print("[BACKUP] stored:", msg)
    finally:
        conn_sock.close()

def start_backup():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 6001))
    s.listen(64)
    print("[BACKUP] listening on 127.0.0.1:6001")
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()

if __name__ == "__main__":
    start_backup()
