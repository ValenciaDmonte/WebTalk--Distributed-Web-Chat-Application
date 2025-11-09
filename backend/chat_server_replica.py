# backend/chat_server_replica.py
import socket, threading, json
from lamport import LamportClock

HOST = "127.0.0.1"
PORT = 6002

clients = {}
lamport = LamportClock()

def send_json(sock, obj):
    try:
        sock.sendall((json.dumps(obj) + "\n").encode())
    except Exception:
        pass

def handle_client(conn, username):
    print(f"[REPLICA] {username} connected")
    buf = ""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk.decode(errors="ignore")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue

                lamport.tick()
                ts = lamport.now()
                t = msg.get("type")

                if t == "private":
                    target, text = msg.get("target"), msg.get("message","")
                    if target in clients:
                        send_json(clients[target], {"from":username,"message":text,"clock":ts})
                        send_json(conn, {"ack":"delivered"})
                    else:
                        send_json(conn, {"ack":"offline"})

                elif t == "join":
                    g = msg.get("message","")
                    send_json(conn, {"info": f"joined {g}"})

                elif t == "group":
                    # mirror primary behaviour if needed later
                    send_json(conn, {"ack":"group_sent"})
    finally:
        if username in clients:
            del clients[username]
        try: conn.close()
        except: pass

def serve_replica():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(128)
    print(f"[REPLICA] listening on {HOST}:{PORT}")
    while True:
        conn, _ = s.accept()
        username = conn.recv(1024).decode(errors="ignore").strip()
        if not username:
            try: conn.close()
            except: pass
            continue
        clients[username] = conn
        threading.Thread(target=handle_client, args=(conn, username), daemon=True).start()

if __name__ == "__main__":
    serve_replica()
