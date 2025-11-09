# backend/gateway/gateway.py
import socket, threading, json, time
from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room

LB_ADDR = ("127.0.0.1", 5000)

app = Flask(__name__, template_folder="../../frontend/templates")
socketio = SocketIO(app, cors_allowed_origins="*")

# Holds: username -> TCP socket to Load Balancer
tcp_conns = {}
locks = {}

def start_reader(username, sock):
    def reader():
        while True:
            try:
                data = sock.recv(4096)
                if not data: break
                # server sends json or plain text; try json
                try:
                    msg = json.loads(data.decode())
                    socketio.emit("message", msg, to=username)
                except:
                    socketio.emit("system", {"text": data.decode()}, to=username)
            except:
                break
        socketio.emit("system", {"text": "Disconnected from server."}, to=username)
    threading.Thread(target=reader, daemon=True).start()

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/chat")
def chat():
    return render_template("index.html")

@socketio.on("register")
def on_register(data):
    """
    data = {username: "..."}
    Establish a TCP connection to Load Balancer and send the username first.
    """
    username = data["username"].strip()
    join_room(username)
    # Connect fresh TCP socket per user
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect(LB_ADDR)
    s.sendall(username.encode())  # first line = username
    tcp_conns[username] = s
    locks[username] = threading.Lock()
    start_reader(username, s)
    emit("system", {"text": f"Connected as {username} via Load Balancer"})

@socketio.on("send_private")
def send_private(data):
    """
    data = {from: "...", to: "...", text: "..."}
    """
    try:
        payload = json.dumps({"type":"private","target":data["to"],"message":data["text"]}).encode()
        with locks[data["from"]]:
            tcp_conns[data["from"]].sendall(payload)
    except Exception as e:
        emit("system", {"text": f"Send failed: {e}"}, to=data["from"])

@socketio.on("join_group")
def join_group(data):
    """
    data = {user: "...", group: "groupname"}
    """
    try:
        payload = json.dumps({"type":"join","message":data["group"]}).encode()
        with locks[data["user"]]:
            tcp_conns[data["user"]].sendall(payload)
    except Exception as e:
        emit("system", {"text": f"Join failed: {e}"}, to=data["user"])

@socketio.on("send_group")
def send_group(data):
    """
    data = {from: "...", group: "groupname", text: "..."}
    """
    try:
        payload = json.dumps({"type":"group","target":data["group"],"message":data["text"]}).encode()
        with locks[data["from"]]:
            tcp_conns[data["from"]].sendall(payload)
    except Exception as e:
        emit("system", {"text": f"Send failed: {e}"}, to=data["from"])

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8080, debug=True)
