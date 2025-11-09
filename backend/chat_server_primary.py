# backend/chat_server_primary.py
import socket, threading, json, time, os
from lamport import LamportClock
from bully_election import Bully

HOST = "127.0.0.1"
PORT = 6000                 # primary client port
BACKUP_ADDR = ("127.0.0.1", 6001)  # replication sink
DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True)

clients = {}         # username -> socket
lamport = LamportClock()

def replicate(msg_obj):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(BACKUP_ADDR)
        s.sendall((json.dumps(msg_obj) + "\n").encode())
        s.close()
    except Exception as e:
        print("[REPLICA] backup not reachable:", e)

def send_json(sock, obj):
    try:
        sock.sendall((json.dumps(obj) + "\n").encode())
    except Exception:
        pass

def handle_client(conn, username):
    print(f"[PRIMARY] {username} connected")
    buf = ""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk.decode(errors="ignore")

            # process complete lines (newline-delimited JSON)
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue

                mtype = msg.get("type")
                lamport.tick()
                ts = lamport.now()

                if mtype == "private":
                    target = msg.get("target")
                    text = msg.get("message", "")
                    # replicate
                    replicate({"kind":"private","from":username,"to":target,"message":text,"clock":ts,"ts":int(time.time())})
                    # deliver
                    if target in clients:
                        send_json(clients[target], {"from": username, "message": text, "clock": ts})
                        send_json(conn, {"ack":"delivered"})
                    else:
                        send_json(conn, {"ack":"offline"})

                elif mtype == "join":
                    # optional – not used if gateway fans out groups as multiple PMs
                    group = msg.get("message", "")
                    send_json(conn, {"info": f"joined {group}"})

                elif mtype == "group":
                    # optional path if you later push real server-side groups
                    g = msg.get("target")
                    text = msg.get("message","")
                    replicate({"kind":"group","group":g,"from":username,"message":text,"clock":ts,"ts":int(time.time())})
                    send_json(conn, {"ack":"group_sent"})
    except Exception as e:
        print("[PRIMARY] error:", e)
    finally:
        if username in clients:
            del clients[username]
        try: conn.close()
        except: pass
        print(f"[PRIMARY] {username} disconnected")

def serve_primary():
    bully = Bully(my_id=1, peers=[])
    bully.start()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(128)
    print(f"[PRIMARY] listening on {HOST}:{PORT}")

    while True:
        conn, _ = s.accept()
        # first read = username (single line)
        username = conn.recv(1024).decode(errors="ignore").strip()
        if not username:
            try: conn.close()
            except: pass
            continue
        clients[username] = conn
        threading.Thread(target=handle_client, args=(conn, username), daemon=True).start()

if __name__ == "__main__":
    serve_primary()
