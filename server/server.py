# server/server.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading

from config import HOST, PORT, CERT, KEY, BUFFER_SIZE
from ssl_config import create_ssl_context, wrap_socket
from connection_manager import register_client, remove_client, get_client, all_clients
from features.protocol import parse_message, send_msg, recv_msg, ProtocolError
from features.rooms import join_room, leave_room, get_clients
from features.ordering import attach_sequence
from features.file_transfer import receive_file, fanout_file

import os as _os

# ── Per-connection send lock ───────────────────────────────────────────
_send_locks: dict = {}
_send_locks_lock = threading.Lock()


def _get_send_lock(conn):
    with _send_locks_lock:
        if conn not in _send_locks:
            _send_locks[conn] = threading.Lock()
        return _send_locks[conn]


def safe_send(conn, data: bytes) -> bool:
    """Thread-safe send. Returns False if the connection is dead."""
    lock = _get_send_lock(conn)
    with lock:
        try:
            conn.sendall(data)
            return True
        except Exception:
            return False


def _safe_send_text(conn, text: str) -> bool:
    return safe_send(conn, text.encode())


def broadcast(room: str, message: str) -> None:
    encoded = message.encode()
    for client in get_clients(room):
        safe_send(client, encoded)


# ── Client handler ─────────────────────────────────────────────────────

def handle_client(conn, addr):
    print(f"[CONNECT] {addr}")
    username    = None
    joined_rooms = set()

    try:
        # ── Handshake: read username ──────────────────────────────────
        raw = conn.recv(1024).decode("utf-8", errors="replace").strip()
        if raw.startswith("USERNAME|"):
            username = raw.split("|", 1)[-1].strip()
        else:
            username = raw

        if not username:
            safe_send(conn, b"ERROR|Username must not be empty")
            return

        if len(username) > 32:
            safe_send(conn, b"ERROR|Username too long (max 32 chars)")
            return

        if not register_client(username, conn):
            safe_send(conn, b"ERROR|Username already taken")
            print(f"[REJECT] {addr} — username '{username}' already taken")
            return

        safe_send(conn, b"OK|Connected to secure server")
        print(f"[AUTH]    {username} @ {addr}")

        # ── Main loop ─────────────────────────────────────────────────
        while True:
            try:
                data = conn.recv(BUFFER_SIZE)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break   # abrupt disconnect — normal during stress tests

            if not data:
                break   # clean close

            try:
                message = parse_message(data.decode("utf-8", errors="replace"))
            except ProtocolError as exc:
                # Send a descriptive error back instead of silently dropping
                _safe_send_text(conn, f"ERROR|{exc}")
                print(f"[PROTO]  {username}: {exc}")
                continue
            except Exception as exc:
                _safe_send_text(conn, f"ERROR|Internal parse error")
                print(f"[ERROR]  parse_message: {exc}")
                continue

            mtype = message["type"]

            if mtype == "join":
                join_room(conn, message["room"])
                joined_rooms.add(message["room"])

            elif mtype == "leave":
                leave_room(conn, message["room"])
                joined_rooms.discard(message["room"])

            elif mtype == "message":
                formatted = attach_sequence(
                    message["room"],
                    f"{username}: {message['content']}"
                )
                broadcast(message["room"], formatted)

            elif mtype == "private":
                target = get_client(message["user"])
                if target:
                    _safe_send_text(
                        target,
                        f"[PRIVATE]{username}: {message['content']}"
                    )
                else:
                    _safe_send_text(conn, f"ERROR|User '{message['user']}' not found")

            elif mtype == "file":
                filename  = message["filename"]
                size      = message["size"]
                room      = message["room"]
                _os.makedirs("received_files", exist_ok=True)
                save_path = _os.path.join("received_files", filename)

                try:
                    receive_file(conn, save_path, size)
                except Exception as fe:
                    print(f"[FILE]   Receive error: {fe}")
                    continue

                # Non-blocking fan-out: each recipient gets its own thread
                fanout_file(
                    sender_conn=conn,
                    filepath=save_path,
                    filename=filename,
                    size=size,
                    recipients=get_clients(room),
                    safe_send_fn=safe_send,
                )

    except Exception as exc:
        print(f"[ERROR]  Unexpected in handle_client({addr}): {exc}")

    finally:
        for room in joined_rooms:
            leave_room(conn, room)
        if username:
            remove_client(username)
            print(f"[DISC]   {username} @ {addr} disconnected")
        with _send_locks_lock:
            _send_locks.pop(conn, None)
        try:
            conn.close()
        except Exception:
            pass


# ── Graceful shutdown ──────────────────────────────────────────────────

_shutdown_event = threading.Event()


def shutdown_server(sock):
    print("\n[SERVER] Shutting down — notifying clients …")
    _shutdown_event.set()
    for uname, conn in all_clients().items():
        try:
            safe_send(conn, b"[Server] Server is shutting down.")
            conn.close()
        except Exception:
            pass
    try:
        sock.close()
    except Exception:
        pass
    print("[SERVER] All connections closed. Goodbye!")


# ── Entry point ────────────────────────────────────────────────────────

def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(20)
    sock.settimeout(1.0)

    ssl_context = create_ssl_context(CERT, KEY)

    print(f"[SERVER] Secure chat server running on {HOST}:{PORT}")
    print("[SERVER] Press Ctrl+C to stop.\n")

    try:
        while not _shutdown_event.is_set():
            try:
                client, addr = sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                secure_client = wrap_socket(ssl_context, client)
            except Exception as tls_err:
                print(f"[TLS]    Handshake failed from {addr}: {tls_err}")
                try:
                    client.close()
                except Exception:
                    pass
                continue

            thread = threading.Thread(
                target=handle_client,
                args=(secure_client, addr),
                daemon=True,
            )
            thread.start()

    except KeyboardInterrupt:
        shutdown_server(sock)


if __name__ == "__main__":
    start_server()
