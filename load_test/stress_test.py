import socket
import ssl
import threading
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
BUFFER_SIZE = 4096

NUM_CLIENTS = 20
MESSAGES_PER_CLIENT = 20


def simulate_client(client_id, results):
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        secure_sock = context.wrap_socket(sock, server_hostname=SERVER_HOST)
        secure_sock.connect((SERVER_HOST, SERVER_PORT))

        secure_sock.send(f"USERNAME|user{client_id}".encode())
        secure_sock.send("JOIN|room1".encode())

        start_time = time.time()

        for i in range(MESSAGES_PER_CLIENT):
            message = f"MSG|room1|Hello from user{client_id} msg{i}"
            secure_sock.send(message.encode())

        end_time = time.time()

        latency = end_time - start_time
        results.append(latency)

        secure_sock.close()

    except Exception as e:
        print("Client error:", e)


def run_load_test():
    threads = []
    results = []

    start_test = time.time()

    for i in range(NUM_CLIENTS):
        t = threading.Thread(target=simulate_client, args=(i, results))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    end_test = time.time()

    total_time = end_test - start_test
    avg_latency = sum(results) / len(results)

    total_messages = NUM_CLIENTS * MESSAGES_PER_CLIENT
    throughput = total_messages / total_time

    print("\n=== Load Test Results ===")
    print(f"Total Clients: {NUM_CLIENTS}")
    print(f"Total Messages: {total_messages}")
    print(f"Total Time: {total_time:.2f} sec")
    print(f"Average Client Latency: {avg_latency:.4f} sec")
    print(f"Throughput: {throughput:.2f} messages/sec")


if __name__ == "__main__":
    run_load_test()