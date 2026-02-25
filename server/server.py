import socket
import threading
from ssl_config import create_ssl_context, wrap_socket
from connection_manager import register_client, remove_client

HOST = "0.0.0.0"
PORT = 5000 

# These point to the files you created in your ssl/ folder
CERT = "ssl/server.crt"
KEY = "ssl/server.key"

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    username = None
    try:
        # Initial greeting and username registration
        conn.send("Enter username: ".encode())
        username = conn.recv(1024).decode().strip()

        if not register_client(username, conn):
            conn.send("ERR_USER_TAKEN".encode())
            conn.close()
            return

        conn.send(f"Welcome {username}! Your connection is now SSL-encrypted.\n".encode())

        # Main loop to receive messages
        while True:
            data = conn.recv(4096)
            if not data:
                break
            
            # This is where Person 2 will later add protocol parsing
            print(f"[{username}] {data.decode()}")

    except Exception as e:
        print(f"Error with {username}: {e}")
    finally:
        if username:
            remove_client(username)
        conn.close()

def start_server():
    # Create the base TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    # Initialize the SSL context using your Person 1 logic
    ssl_context = create_ssl_context(CERT, KEY)
    print(f"Secure Server listening on port {PORT}...")

    while True:
        # Accept a new raw TCP connection
        client_sock, addr = server_socket.accept()
        
        # Secure the connection with SSL before doing anything else
        secure_sock = wrap_socket(ssl_context, client_sock)
        
        # Concurrency: One thread per client handles simultaneous users
        t = threading.Thread(target=handle_client, args=(secure_sock, addr))
        t.start()

if __name__ == "__main__":
    start_server()
