import threading

# A shared dictionary to store 'username': socket_object
clients = {}
# A lock is mandatory to prevent two threads from writing to the list at once
lock = threading.Lock()

def register_client(username, conn):
    with lock:
        # Prevents duplicate usernames
        if username in clients:
            return False
        clients[username] = conn
        print(f"User '{username}' registered.")
        return True

def remove_client(username):
    with lock:
        # Safely removes the client when they disconnect
        if username in clients:
            del clients[username]
            print(f"User '{username}' removed.")

def get_all_clients():
    with lock:
        return clients
