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
KEY = "ssl/server.key"

BUFFER_SIZE = 4096


def broadcast(room, message):
    clients = get_clients(room)

    for client in clients:
        try:
            client.send(message.encode())
        except:
            pass


def handle_client(conn, addr):
    print("Connected:", addr)

    username = None

    try:
        username = conn.recv(1024).decode().strip()

        if not register_client(username, conn):
            conn.send("Username already taken".encode())
            conn.close()
            return

        conn.send("Connected to secure server".encode())

        while True:
            data = conn.recv(BUFFER_SIZE)

            if not data:
                break

            message = parse_message(data.decode())

            if message["type"] == "join":
                join_room(conn, message["room"])

            elif message["type"] == "leave":
                leave_room(conn, message["room"])

            elif message["type"] == "message":
                formatted = attach_sequence(
                    message["room"],
                    f"{username}: {message['content']}"
                )

                broadcast(message["room"], formatted)

            elif message["type"] == "private":

                target = get_client(message["user"])

                if target:
                    target.send(
                        f"[PRIVATE]{username}: {message['content']}".encode()
                    )

            elif message["type"] == "file":

                filename = message["filename"]
                size = message["size"]
                room = message["room"]

                # Save received files in a dedicated folder
                os.makedirs("received_files", exist_ok=True)
                save_path = os.path.join("received_files", filename)

                receive_file(conn, save_path, size)

                # Only forward if the sender is actually in the room
                clients = get_clients(room)

                for client in clients:
                    if client != conn:
                        try:
                            client.send(
                                f"FILE_INCOMING|{filename}|{size}".encode()
                            )
                            send_file(client, save_path)
                        except Exception as fe:
                            print(f"Failed to forward file to a client: {fe}")

    except Exception as e:
        print("Error:", e)

    finally:
        if username:
            remove_client(username)

        conn.close()


def shutdown_server(sock):
    print("\n[Server] Shutting down...")

    from connection_manager import clients as client_map

    for username, conn in list(client_map.items()):
        try:
            conn.send("[Server] Server is shutting down.".encode())
            conn.close()
        except:
            pass

    try:
        sock.close()
    except:
        pass

    print("[Server] All connections closed. Goodbye!")


def start_server():

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(10)

    ssl_context = create_ssl_context(CERT, KEY)

    # Timeout lets accept() unblock every second so Ctrl+C is caught on Windows
    sock.settimeout(1.0)

    print("Secure chat server running on port", PORT)
    print("Press Ctrl+C to stop the server.\n")

    try:
        while True:
            try:
                client, addr = sock.accept()
            except socket.timeout:
                # No connection in last 1s — loop back and check for Ctrl+C
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
