import socket
import ssl
import threading
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
BUFFER_SIZE = 4096

NUM_CLIENTS = 20
MESSAGES_PER_CLIENT = 20


def simulate_client(client_id, results, errors):
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        secure_sock = context.wrap_socket(sock, server_hostname=SERVER_HOST)
        secure_sock.connect((SERVER_HOST, SERVER_PORT))

        # Send only the username — no prefix
        username = f"user{client_id}"
        secure_sock.send(username.encode())

        # Wait for server ack
        ack = secure_sock.recv(BUFFER_SIZE).decode()
        if "Connected" not in ack:
            errors.append(f"{username}: bad ack: {ack}")
            secure_sock.close()
            return

        time.sleep(0.1)
        secure_sock.send("JOIN|room1".encode())
        time.sleep(0.1)

        start_time = time.time()
        for i in range(MESSAGES_PER_CLIENT):
            secure_sock.send(f"MSG|room1|Hello from {username} msg{i}".encode())
            time.sleep(0.05)

        results.append(time.time() - start_time)

        time.sleep(0.2)
        secure_sock.close()

    except Exception as e:
        errors.append(f"user{client_id}: {e}")


def run_load_test():
    threads = []
    results = []
    errors  = []

    print(f"Starting load test: {NUM_CLIENTS} clients x {MESSAGES_PER_CLIENT} messages\n")
    start_test = time.time()

    for i in range(NUM_CLIENTS):
        t = threading.Thread(target=simulate_client, args=(i, results, errors))
        threads.append(t)
        t.start()
        time.sleep(0.1)

    for t in threads:
        t.join()

    total_time  = time.time() - start_test
    successful  = len(results)
    total_msgs  = successful * MESSAGES_PER_CLIENT
    throughput  = total_msgs / total_time if total_time > 0 else 0
    avg_latency = sum(results) / successful if successful > 0 else 0

    print("=== Load Test Results ===")
    print(f"Total Clients:       {NUM_CLIENTS}")
    print(f"Successful Clients:  {successful}")
    print(f"Failed Clients:      {len(errors)}")
    print(f"Total Messages Sent: {total_msgs}")
    print(f"Total Time:          {total_time:.2f} sec")
    print(f"Avg Client Latency:  {avg_latency:.4f} sec")
    print(f"Throughput:          {throughput:.2f} messages/sec")

    if errors:
        print(f"\nFailed clients:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    run_load_test()
