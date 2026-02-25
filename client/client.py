import socket
import ssl
import threading
import os

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

BUFFER_SIZE = 4096


def create_ssl_connection():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_sock = context.wrap_socket(sock, server_hostname=SERVER_HOST)
    secure_sock.connect((SERVER_HOST, SERVER_PORT))

    return secure_sock


def receive_messages(sock):
    while True:
        try:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                print("Disconnected from server.")
                break

            message = data.decode()

            # Handle file reception
            if message.startswith("FILE_INCOMING"):
                _, filename, filesize = message.split("|")
                filesize = int(filesize)

                print(f"Receiving file: {filename}")

                with open("received_" + filename, "wb") as f:
                    remaining = filesize
                    while remaining > 0:
                        chunk = sock.recv(min(BUFFER_SIZE, remaining))
                        f.write(chunk)
                        remaining -= len(chunk)

                print("File received successfully.")
            else:
                print(message)

        except Exception as e:
            print("Error receiving data:", e)
            break


def send_file(sock, filepath, room):
    if not os.path.exists(filepath):
        print("File not found.")
        return

    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    metadata = f"FILE|{room}|{filename}|{filesize}"
    sock.send(metadata.encode())

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            sock.send(chunk)

    print("File sent successfully.")


def main():
    sock = create_ssl_connection()

    username = input("Enter username: ")
    sock.send(f"USERNAME|{username}".encode())

    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    print("\nCommands:")
    print("/join room_name")
    print("/leave room_name")
    print("/msg room_name message")
    print("/private username message")
    print("/file room_name filepath")
    print("/quit\n")

    while True:
        command = input()

        if command.startswith("/join"):
            _, room = command.split()
            sock.send(f"JOIN|{room}".encode())

        elif command.startswith("/leave"):
            _, room = command.split()
            sock.send(f"LEAVE|{room}".encode())

        elif command.startswith("/msg"):
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("Invalid command.")
                continue
            room = parts[1]
            message = parts[2]
            sock.send(f"MSG|{room}|{message}".encode())

        elif command.startswith("/private"):
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("Invalid command.")
                continue
            user = parts[1]
            message = parts[2]
            sock.send(f"PRIVATE|{user}|{message}".encode())

        elif command.startswith("/file"):
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("Invalid command.")
                continue
            room = parts[1]
            filepath = parts[2]
            send_file(sock, filepath, room)

        elif command == "/quit":
            sock.close()
            break

        else:
            print("Unknown command.")


if __name__ == "__main__":
    main()