# backend/bully_election.py
import socket, threading, time

class Bully:
    """
    Minimal bully scaffold. In this single-primary demo, we just expose API
    and print role; can be extended with more nodes (ports) to fully elect.
    """
    def __init__(self, my_id, peers):
        self.my_id = my_id
        self.peers = peers  # [(id,host,port_for_election)]
        self.leader = my_id

    def start(self):
        print(f"[BULLY] Node {self.my_id} assumes leader (single-node demo).")

    def is_leader(self):
        return self.leader == self.my_id
