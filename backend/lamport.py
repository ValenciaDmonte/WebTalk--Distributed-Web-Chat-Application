# backend/lamport.py
import threading

class LamportClock:
    def __init__(self):
        self.val = 0
        self.lock = threading.Lock()

    def tick(self):
        with self.lock:
            self.val += 1
            return self.val

    def update(self, received):
        with self.lock:
            self.val = max(self.val, int(received)) + 1
            return self.val

    def now(self):
        with self.lock:
            return self.val
