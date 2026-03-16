import socket
import ssl
import threading
import os

SERVER = "127.0.0.1"
PORT = 5000

BUFFER_SIZE = 4096


def create_connection():

    context = ssl.create_default_context()

    context.load_verify_locations("ssl/server.crt")

    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    secure_sock = context.wrap_socket(sock, server_hostname=SERVER)

    secure_sock.connect((SERVER, PORT))

    return secure_sock


def receive(sock):

    while True:

        try:

            data = sock.recv(BUFFER_SIZE)

            if not data:
                break

            msg = data.decode()

            if msg.startswith("FILE_INCOMING"):

                _, filename, size = msg.split("|")

                size = int(size)

                with open("received_" + filename, "wb") as f:

                    remaining = size

                    while remaining > 0:

                        chunk = sock.recv(min(BUFFER_SIZE, remaining))

                        f.write(chunk)

                        remaining -= len(chunk)

                print("File received:", filename)

            else:
                print(msg)

        except:
            break


def send_file(sock, path, room):

    if not os.path.exists(path):
        print("File not found")
        return

    size = os.path.getsize(path)

    name = os.path.basename(path)

    sock.send(f"FILE|{room}|{name}|{size}".encode())

    with open(path, "rb") as f:

        while True:

            data = f.read(BUFFER_SIZE)

            if not data:
                break

            sock.sendall(data)


def main():

    sock = create_connection()

    username = input("Username: ")

    sock.send(username.encode())

    thread = threading.Thread(target=receive, args=(sock,))
    thread.daemon = True
    thread.start()

    while True:

        cmd = input()

        if cmd.startswith("/join"):

            _, room = cmd.split()

            sock.send(f"JOIN|{room}".encode())

        elif cmd.startswith("/leave"):

            _, room = cmd.split()

            sock.send(f"LEAVE|{room}".encode())

        elif cmd.startswith("/msg"):

            parts = cmd.split(" ", 2)

            sock.send(f"MSG|{parts[1]}|{parts[2]}".encode())

        elif cmd.startswith("/private"):

            parts = cmd.split(" ", 2)

            sock.send(f"PRIVATE|{parts[1]}|{parts[2]}".encode())

        elif cmd.startswith("/file"):

            parts = cmd.split(" ", 2)

            send_file(sock, parts[2], parts[1])

        elif cmd == "/quit":

            sock.close()

            break


if __name__ == "__main__":
    main()