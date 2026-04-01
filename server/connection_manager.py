# server/connection_manager.py
import threading

clients: dict = {}
_lock = threading.Lock()


def register_client(username: str, conn) -> bool:
    """Atomically register *username*. Returns False if already taken."""
    with _lock:
        if username in clients:
            return False
        clients[username] = conn
        return True


def remove_client(username: str) -> None:
    with _lock:
        clients.pop(username, None)


def get_client(username: str):
    with _lock:
        return clients.get(username)


def all_clients() -> dict:
    """Return a snapshot copy so callers don't hold the lock."""
    with _lock:
        return dict(clients)
