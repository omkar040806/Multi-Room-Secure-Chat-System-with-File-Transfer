import threading

clients = {}
lock = threading.Lock()


def register_client(username, conn):
    with lock:
        if username in clients:
            return False
        clients[username] = conn
        return True


def remove_client(username):
    with lock:
        if username in clients:
            del clients[username]


def get_client(username):
    with lock:
        return clients.get(username)
