# features/file_transfer.py
# Handles receiving, sending, and concurrently forwarding files between clients using chunked transfer and threading.

import threading
import os
from config import BUFFER_SIZE


def receive_file(conn, filepath: str, size: int) -> None:
    # Receives a file from a connection and writes it in chunks until the expected size is reached.
    received = 0
    with open(filepath, "wb") as f:
        while received < size:
            chunk = conn.recv(min(BUFFER_SIZE, size - received))
            if not chunk:
                raise ConnectionError(
                    f"Connection closed after {received}/{size} bytes"
                )
            f.write(chunk)
            received += len(chunk)
    print(f"[FILE] Received: {os.path.basename(filepath)} ({size} bytes)")


def send_file(conn, filepath: str) -> None:
    # Sends a file over a connection in fixed-size chunks.
    with open(filepath, "rb") as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            conn.sendall(data)


def fanout_file(
    sender_conn,
    filepath: str,
    filename: str,
    size: int,
    recipients: list,
    safe_send_fn,
) -> None:
    # Forwards a file to multiple clients concurrently using separate threads to avoid blocking.

    def _send_to(conn):
        try:
            safe_send_fn(conn, f"FILE_INCOMING|{filename}|{size}".encode())
            send_file(conn, filepath)
        except Exception as exc:
            print(f"[FILE] Forward error to {conn}: {exc}")

    threads = [
        threading.Thread(target=_send_to, args=(conn,), daemon=True)
        for conn in recipients
        if conn is not sender_conn
    ]
    for t in threads:
        t.start()
