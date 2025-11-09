# backend/load_balancer.py
import socket, threading

SERVERS = [("127.0.0.1", 6000), ("127.0.0.1", 6002)]  # primary + replica
rr = 0
lock = threading.Lock()

def pipe(src, dest):
    try:
        while True:
            data = src.recv(4096)
            if not data: break
            dest.sendall(data)
    except:
        pass
    finally:
        try: src.close()
        except: pass
        try: dest.close()
        except: pass

def handle_client(client_sock, addr):
    global rr
    with lock:
        target = SERVERS[rr % len(SERVERS)]
        rr += 1

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.connect(target)

    # First message from client is the username; forward to server
    username = client_sock.recv(1024)
    server_sock.sendall(username)

    threading.Thread(target=pipe, args=(client_sock, server_sock), daemon=True).start()
    threading.Thread(target=pipe, args=(server_sock, client_sock), daemon=True).start()

def start_lb():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 5000))
    s.listen(256)
    print("[LB] listening on 127.0.0.1:5000")
    while True:
        c, addr = s.accept()
        threading.Thread(target=handle_client, args=(c, addr), daemon=True).start()

if __name__ == "__main__":
    start_lb()
