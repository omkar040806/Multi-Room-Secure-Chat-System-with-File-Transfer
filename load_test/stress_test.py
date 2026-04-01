# load_test/stress_test.py
import matplotlib.pyplot as plt
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import ssl
import threading
import time
import random

from config import SERVER_IP, PORT, CERT, BUFFER_SIZE, NUM_CLIENTS, MESSAGES_PER_CLIENT

ROOM = "stress-room"


def simulate_client(client_id: int, results: list, errors: list) -> None:
    username = f"stress_user{client_id}"
    try:
        # TLS context — CERT_REQUIRED, loads real certificate 
        context = ssl.create_default_context()
        context.load_verify_locations(CERT)
        context.check_hostname = False
        context.verify_mode    = ssl.CERT_REQUIRED

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        secure_sock = context.wrap_socket(sock, server_hostname=SERVER_IP)
        secure_sock.connect((SERVER_IP, PORT))

        # Auth 
        secure_sock.sendall(username.encode())
        ack = secure_sock.recv(BUFFER_SIZE).decode("utf-8", errors="replace")

        if "already taken" in ack or ack.startswith("ERROR"):
            errors.append(f"{username}: rejected — {ack}")
            secure_sock.close()
            return

        if "Connected" not in ack and "OK" not in ack:
            errors.append(f"{username}: unexpected ack: {ack!r}")
            secure_sock.close()
            return

        time.sleep(0.05)

        # Join room 
        secure_sock.sendall(f"JOIN|{ROOM}".encode())
        time.sleep(0.05)

        # Mixed message workload 
        start = time.time()

        for i in range(MESSAGES_PER_CLIENT):
            choice = random.random()

            if choice < 0.70:
                # Broadcast to room
                secure_sock.sendall(
                    f"MSG|{ROOM}|Hello from {username} #{i}".encode()
                )

            elif choice < 0.85:
                # Private message to a random other user
                target = f"stress_user{random.randint(0, NUM_CLIENTS - 1)}"
                if target != username:
                    secure_sock.sendall(
                        f"PRIVATE|{target}|ping from {username}".encode()
                    )
                else:
                    secure_sock.sendall(
                        f"MSG|{ROOM}|fallback msg {i}".encode()
                    )

            else:
                # Leave and re-join (tests room lifecycle)
                alt_room = f"room{random.randint(1, 5)}"
                secure_sock.sendall(f"JOIN|{alt_room}".encode())
                time.sleep(0.02)
                secure_sock.sendall(f"LEAVE|{alt_room}".encode())

            time.sleep(0.04)

        elapsed = time.time() - start
        results.append(elapsed)

        time.sleep(0.1)
        secure_sock.close()

    except Exception as exc:
        errors.append(f"{username}: {exc}")


def run_load_test(
    num_clients: int = NUM_CLIENTS,
    msgs_each:   int = MESSAGES_PER_CLIENT,
) -> None:
    threads = []
    results: list[float] = []
    errors:  list[str]   = []

    print(f"┌─ Stress test ────────────────────────────────────────────")
    print(f"│  Target  : {SERVER_IP}:{PORT}  (TLS · CERT_REQUIRED)")
    print(f"│  Clients : {num_clients}  ×  {msgs_each} messages each")
    print(f"└──────────────────────────────────────────────────────────\n")

    test_start = time.time()

    for i in range(num_clients):
        t = threading.Thread(
            target=simulate_client,
            args=(i, results, errors),
            daemon=True,
        )
        threads.append(t)
        t.start()
        time.sleep(0.08)   # stagger to avoid thundering-herd on TLS handshakes

    for t in threads:
        t.join(timeout=30)

    total_time  = time.time() - test_start
    successful  = len(results)
    failed      = len(errors)
    total_msgs  = successful * msgs_each
    throughput  = total_msgs / total_time if total_time > 0 else 0
    avg_latency = sum(results) / successful if successful else 0

    print("\n=== Load Test Results " + "=" * 40)
    print(f"  Total Clients      : {num_clients}")
    print(f"  Successful         : {successful}")
    print(f"  Failed             : {failed}")
    print(f"  Total Messages     : {total_msgs}")
    print(f"  Total Time         : {total_time:.2f} s")
    print(f"  Avg Client Latency : {avg_latency:.4f} s")
    print(f"  Throughput         : {throughput:.2f} msg/s")

    if errors:
        print(f"\n  Failed clients ({failed}):")
        for e in errors:
            print(f"    ✗ {e}")
    else:
        print("\n  ✓ No failures!")
    print("=" * 62)

    return {
        "clients": num_clients,
        "success": successful,
        "failed": failed,
        "throughput": throughput,
        "latency": avg_latency,
        "total_time": total_time
    }

def plot_graphs(clients, throughputs, latencies, successes):
    
    # Throughput vs Clients
    plt.figure()
    plt.plot(clients, throughputs, marker='o')
    plt.xlabel("Number of Clients")
    plt.ylabel("Throughput (msg/s)")
    plt.title("Throughput vs Number of Clients")
    plt.grid()
    plt.savefig("throughput.png")

    # Latency vs Clients
    plt.figure()
    plt.plot(clients, latencies, marker='o')
    plt.xlabel("Number of Clients")
    plt.ylabel("Average Latency (s)")
    plt.title("Latency vs Number of Clients")
    plt.grid()
    plt.savefig("latency.png")

    # Success Rate
    plt.figure()
    plt.plot(clients, successes, marker='o')
    plt.xlabel("Number of Clients")
    plt.ylabel("Successful Clients")
    plt.title("Scalability (Success vs Load)")
    plt.grid()
    plt.savefig("success_rate.png")

    print("\nGraphs saved:")
    print(" - throughput.png")
    print(" - latency.png")
    print(" - success_rate.png")

def run_experiments():
    client_sizes = [5, 10, 20, 40]

    throughputs = []
    latencies = []
    successes = []

    print("\nRunning scalability experiments...\n")

    for c in client_sizes:
        print(f"\n=== Running test with {c} clients ===")
        result = run_load_test(num_clients=c, msgs_each=MESSAGES_PER_CLIENT)

        throughputs.append(result["throughput"])
        latencies.append(result["latency"])
        successes.append(result["success"])

    plot_graphs(client_sizes, throughputs, latencies, successes)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SecureChat stress test")
    parser.add_argument("--clients", type=int, default=NUM_CLIENTS)
    parser.add_argument("--msgs",    type=int, default=MESSAGES_PER_CLIENT)
    args = parser.parse_args()
    run_experiments()
