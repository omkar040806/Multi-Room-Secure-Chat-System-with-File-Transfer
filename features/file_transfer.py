BUFFER_SIZE = 4096


def receive_file(conn, filename, size):
    received = 0

    with open(filename, "wb") as f:
        while received < size:
            data = conn.recv(BUFFER_SIZE)

            if not data:
                break

            f.write(data)
            received += len(data)

    print("File received:", filename)


def send_file(conn, filepath):

    with open(filepath, "rb") as f:

        while True:

            data = f.read(BUFFER_SIZE)

            if not data:
                break

            conn.sendall(data)