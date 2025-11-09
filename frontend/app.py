from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, disconnect
import requests
import socket
import threading
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app, cors_allowed_origins="*")

API_BASE = "http://127.0.0.1:7000"   # your REST API
LB_ADDR  = ("127.0.0.1", 5000)       # load balancer tcp

# Map Socket.IO session id -> { 'username': str, 'sock': tcp-socket, 'rx': thread }
clients = {}

# ---------------- HTTP pages ----------------
@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for("chat_page"))
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        u = request.form["username"].strip()
        p = request.form["password"].strip()
        r = requests.post(f"{API_BASE}/signup", json={"username": u, "password": p})
        if r.ok and r.json().get("ok"):
            return redirect(url_for("home"))
        return render_template("signup.html", error="Signup failed. Try a different username.")
    return render_template("signup.html")

@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username", "").strip()
    p = request.form.get("password", "").strip()
    r = requests.post(f"{API_BASE}/login", json={"username": u, "password": p})
    if r.ok and r.json().get("ok"):
        session["username"] = u
        return redirect(url_for("chat_page"))
    return render_template("index.html", error="Invalid credentials")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

@app.route("/chat")
def chat_page():
    if "username" not in session:
        return redirect(url_for("home"))
    return render_template("chat.html", username=session["username"])

# ------------- Socket.IO <-> TCP bridge -------------

def tcp_reader_loop(sid):
    """Read messages from LB TCP socket and push to that user's Socket.IO client."""
    try:
        sock = clients[sid]["sock"]
        while True:
            data = sock.recv(4096)
            if not data:
                break
            # deliver raw lines back to the browser
            socketio.emit("message", data.decode(errors="ignore"), room=sid)
    except Exception as e:
        socketio.emit("message", f"[gateway] connection closed: {e}", room=sid)
    finally:
        # cleanup
        c = clients.get(sid)
        if c:
            try:
                c["sock"].close()
            except:
                pass
        clients.pop(sid, None)
        try:
            disconnect(sid=sid)
        except:
            pass

@socketio.on("connect")
def on_connect():
    # Wait for register to actually wire the TCP link
    emit("gateway", "connected to gateway")

@socketio.on("disconnect")
def on_disconnect():
    c = clients.pop(request.sid, None)
    if c:
        try:
            c["sock"].close()
        except:
            pass

@socketio.on("register")
def on_register(username):
    """
    Browser calls this once after /chat loads.
    We open a PERSISTENT TCP socket to the load balancer, send username handshake,
    and start a thread to read messages from LB and emit to this socket.io client.
    """
    sid = request.sid
    # if already registered, ignore
    if sid in clients:
        return

    # open TCP to LB
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(LB_ADDR)
    except Exception as e:
        emit("message", f"[gateway] cannot reach load balancer: {e}")
        return

    # LB expects: it immediately asks for username; send username
    try:
        # read LB's "Enter username:" prompt if any (non-fatal if not read)
        s.settimeout(0.2)
        try:
            _ = s.recv(1024)
        except:
            pass
        s.settimeout(None)
        s.sendall((username + "\n").encode())
    except Exception as e:
        emit("message", f"[gateway] register failed: {e}")
        try: s.close()
        except: pass
        return

    # Save & start reader thread
    t = threading.Thread(target=tcp_reader_loop, args=(sid,), daemon=True)
    clients[sid] = {"username": username, "sock": s, "rx": t}
    t.start()
    emit("gateway", f"registered as {username}")

@socketio.on("send_pm")
def on_send_pm(data):
    sid = request.sid
    c = clients.get(sid)
    if not c:
        emit("message", "[gateway] not registered")
        return

    to = data.get("to", "").strip()
    text = data.get("text", "").strip()
    if not to or not text:
        emit("message", "[gateway] missing to/text")
        return

    obj = {"type": "private", "target": to, "message": text}
    try:
        c["sock"].sendall((json.dumps(obj) + "\n").encode())
    except Exception as e:
        emit("message", f"[gateway] send failed: {e}")


@socketio.on("send_group")
def on_send_group(data):
    sid = request.sid
    c = clients.get(sid)
    if not c:
        emit("message", "[gateway] not registered")
        return

    gid = data.get("group_id")
    gname = data.get("group_name", "")
    text = data.get("text", "").strip()
    me = c["username"]

    if not gid or not text:
        emit("message", "[gateway] missing group_id/text")
        return

    try:
        r = requests.get(f"{API_BASE}/group/members", params={"group_id": gid}, timeout=3)
        members = r.json().get("members", [])
    except Exception as e:
        emit("message", f"[gateway] cannot fetch group members: {e}")
        return

    delivered = 0
    for m in members:
        if m == me:
            continue
        obj = {"type": "private", "target": m, "message": f"[#{gname}] {me}: {text}"}
        try:
            c["sock"].sendall((json.dumps(obj) + "\n").encode())
            delivered += 1
        except:
            pass

    emit("message", f"[gateway] group '{gname}' fan-out to {delivered} member(s)")



if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8080, debug=True)
