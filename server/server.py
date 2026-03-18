import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading

from ssl_config import create_ssl_context, wrap_socket
from connection_manager import register_client, remove_client, get_client
from features.protocol import parse_message
from features.rooms import join_room, leave_room, get_clients
from features.ordering import attach_sequence
from features.file_transfer import receive_file, send_file

HOST = "0.0.0.0"
PORT = 5000
CERT = "ssl/server.crt"
KEY  = "ssl/server.key"
BUFFER_SIZE = 4096

send_locks = {}
send_locks_lock = threading.Lock()


def get_send_lock(conn):
    with send_locks_lock:
        if conn not in send_locks:
            send_locks[conn] = threading.Lock()
        return send_locks[conn]


def safe_send(conn, data):
    lock = get_send_lock(conn)
    with lock:
        try:
            conn.send(data)
            return True
        except Exception:
            return False


def broadcast(room, message):
    encoded = message.encode()
    for client in get_clients(room):
        safe_send(client, encoded)


def handle_client(conn, addr):
    print("Connected:", addr)
    username = None
    joined_rooms = set()

    try:
        raw = conn.recv(1024).decode().strip()
        username = raw.split("|")[-1] if raw.startswith("USERNAME|") else raw

        if not username:
            conn.close()
            return

        if not register_client(username, conn):
            safe_send(conn, b"Username already taken")
            conn.close()
            return

        safe_send(conn, b"Connected to secure server")

        while True:
            try:
                data = conn.recv(BUFFER_SIZE)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                # Client disconnected abruptly — normal during stress test
                break

            if not data:
                break  # clean disconnect

            try:
                message = parse_message(data.decode())
            except Exception:
                continue

            if message["type"] == "join":
                join_room(conn, message["room"])
                joined_rooms.add(message["room"])

            elif message["type"] == "leave":
                leave_room(conn, message["room"])
                joined_rooms.discard(message["room"])

            elif message["type"] == "message":
                formatted = attach_sequence(
                    message["room"],
                    f"{username}: {message['content']}"
                )
                broadcast(message["room"], formatted)

            elif message["type"] == "private":
                target = get_client(message["user"])
                if target:
                    safe_send(target,
                        f"[PRIVATE]{username}: {message['content']}".encode()
                    )

            elif message["type"] == "file":
                filename = message["filename"]
                size     = message["size"]
                room     = message["room"]
                os.makedirs("received_files", exist_ok=True)
                save_path = os.path.join("received_files", filename)
                receive_file(conn, save_path, size)
                for client in get_clients(room):
                    if client != conn:
                        try:
                            safe_send(client,
                                f"FILE_INCOMING|{filename}|{size}".encode()
                            )
                            send_file(client, save_path)
                        except Exception as fe:
                            print(f"File forward error: {fe}")

    except Exception as e:
        print("Unexpected error:", e)

    finally:
        for room in joined_rooms:
            leave_room(conn, room)
        if username:
            remove_client(username)
        with send_locks_lock:
            send_locks.pop(conn, None)
        try:
            conn.close()
        except Exception:
            pass


def shutdown_server(sock):
    print("\n[Server] Shutting down...")
    from connection_manager import clients as client_map
    for uname, conn in list(client_map.items()):
        try:
            safe_send(conn, b"[Server] Server is shutting down.")
            conn.close()
        except Exception:
            pass
    try:
        sock.close()
    except Exception:
        pass
    print("[Server] All connections closed. Goodbye!")


def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(20)
    ssl_context = create_ssl_context(CERT, KEY)
    sock.settimeout(1.0)

    print("Secure chat server running on port", PORT)
    print("Press Ctrl+C to stop the server.\n")

    try:
        while True:
            try:
                client, addr = sock.accept()
            except socket.timeout:
                continue
            secure_client = wrap_socket(ssl_context, client)
            thread = threading.Thread(
                target=handle_client,
                args=(secure_client, addr)
            )
            thread.daemon = True
            thread.start()

    except KeyboardInterrupt:
        shutdown_server(sock)


if __name__ == "__main__":
    start_server()
