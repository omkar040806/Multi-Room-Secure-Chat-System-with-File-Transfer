# Multi-Room Secure Chat System with File Transfer

A multi-client, multi-room chat server built on raw TCP sockets with TLS 1.2/1.3 encryption. Written in Python, it supports room-based broadcasting, private messaging, chunked file transfer, sequenced message ordering, and a stress-test harness.

---

## Project Structure

```
Multi-Room-Secure-Chat-System-with-File-Transfer/
├── config.py                  # Central configuration (host, port, TLS paths, buffer size)
├── server/
│   ├── server.py              # Main server: accepts connections, dispatches threads
│   ├── connection_manager.py  # Thread-safe username → socket registry
│   └── ssl_config.py          # TLS context creation and socket wrapping
├── features/
│   ├── protocol.py            # Message parser (JOIN/LEAVE/MSG/PRIVATE/FILE)
│   ├── rooms.py               # Room lifecycle and per-room client lists
│   ├── ordering.py            # Per-room sequence number attachment
│   └── file_transfer.py       # Chunked receive, send, and concurrent fan-out
├── client/
│   ├── client.py              # CLI client (connect, send commands, receive files)
│   └── client_gui.py          # GUI client
├── load_test/
│   └── stress_test.py         # Concurrent load tester with matplotlib output
└── README.md
```

---

## Requirements

- Python 3.8+
- `matplotlib` (stress test only)
- OpenSSL (for certificate generation)

Install dependencies:

```bash
pip install matplotlib
```

---

## SSL Certificate Setup

Both the server and client need a self-signed certificate. Generate one with:

```bash
openssl req -new -x509 -days 365 -nodes \
  -out server.crt -keyout server.key
```

Place the files:

| File         | Server path        | Client path        |
|--------------|--------------------|--------------------|
| `server.crt` | `server/ssl/`      | `client/ssl/`      |
| `server.key` | `server/ssl/`      | *(not needed)*     |

The server loads them via `config.py` (`CERT` and `KEY`). The CLI client hardcodes `ssl/server.crt` relative to its working directory, so run it from inside the `client/` folder or adjust the path in `client.py`.

---

## Configuration (`config.py`)

| Variable            | Default       | Description                            |
|---------------------|---------------|----------------------------------------|
| `HOST`              | `0.0.0.0`     | Interface the server binds to          |
| `SERVER_IP`         | `127.0.0.1`   | IP clients connect to                  |
| `PORT`              | `5000`        | TCP port                               |
| `CERT`              | `ssl/server.crt` | TLS certificate path                |
| `KEY`               | `ssl/server.key` | TLS private key path                |
| `BUFFER_SIZE`       | `4096`        | Socket read chunk size (bytes)         |
| `NUM_CLIENTS`       | `20`          | Default stress-test client count       |
| `MESSAGES_PER_CLIENT` | `20`        | Default messages per stress client     |

All values can be overridden with environment variables (`CHAT_HOST`, `CHAT_SERVER_IP`, `CHAT_PORT`, `CHAT_CERT`, `CHAT_KEY`).

---

## Running the Server

```bash
cd Multi-Room-Secure-Chat-System-with-File-Transfer-main
python server/server.py
```

The server listens on `0.0.0.0:5000` by default and prints connection, authentication, and disconnection events to stdout. Press `Ctrl+C` for a graceful shutdown — it notifies all connected clients before closing.

---

## Running the CLI Client

```bash
cd Multi-Room-Secure-Chat-System-with-File-Transfer-main/client
python client.py
```

You will be prompted for a username (max 32 characters, must be unique). After connecting, use the following commands:

| Command                         | Description                          |
|---------------------------------|--------------------------------------|
| `/join <room>`                  | Join (or create) a chat room         |
| `/leave <room>`                 | Leave a chat room                    |
| `/msg <room> <message>`         | Send a message to a room             |
| `/private <username> <message>` | Send a private message to a user     |
| `/file <room> <filepath>`       | Upload a file to all room members    |
| `/quit`                         | Disconnect and exit                  |

Received files are saved in the current directory as `received_<filename>`.

---

## Wire Protocol

All messages are `|`-delimited ASCII strings:

```
USERNAME|<name>                         # initial handshake
JOIN|<room>
LEAVE|<room>
MSG|<room>|<message>
PRIVATE|<username>|<message>
FILE|<room>|<filename>|<filesize_bytes>
```

The server responds with `OK|Connected to secure server` on successful login, or `ERROR|<reason>` on failure. Broadcast messages arrive prefixed with a room sequence number:

```
[room_name][42] alice: hello
```

Incoming file notifications arrive as:

```
FILE_INCOMING|<filename>|<size>
```

followed immediately by raw binary file bytes.

---

## Architecture

### Server

- **One thread per client** — `threading.Thread` spawned in `server.py` for each accepted connection.
- **Thread-safe connection registry** — `connection_manager.py` uses a `threading.Lock` to guard the username → socket dict; duplicate usernames are rejected atomically.
- **Room management** — `rooms.py` maintains a `dict` of room name → `{clients, sequence, seq_lock}`. Rooms are created on first join and deleted when the last member leaves.
- **Per-connection send lock** — `server.py` keeps a `dict` of `conn → Lock` so concurrent threads can send to the same socket without interleaving.
- **Message ordering** — `ordering.py` calls `rooms.get_next_sequence()` (fine-grained per-room lock) and prepends `[room][seq]` to every broadcast.
- **File fan-out** — `file_transfer.fanout_file()` spawns one daemon thread per recipient so a slow receiver cannot block the sender's thread.

### TLS

`ssl_config.py` builds a `PROTOCOL_TLS_SERVER` context with:
- Minimum version: **TLS 1.2**
- Cipher suite: `ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!MD5:!RC4`

The client verifies the server certificate (`CERT_REQUIRED`) but has `check_hostname = False` (suitable for self-signed certs with a fixed IP).

---

## Load Testing

```bash
cd Multi-Room-Secure-Chat-System-with-File-Transfer-main
python load_test/stress_test.py
```

Each simulated client authenticates, joins `stress-room`, and sends `MESSAGES_PER_CLIENT` messages with a randomised mix of:
- **70%** room broadcasts (`MSG`)
- **15%** private messages to a random peer (`PRIVATE`)
- **15%** leave/rejoin a random alternate room (room lifecycle stress)

The script measures per-client latency, aggregates throughput and failure counts, and generates a matplotlib chart. Adjust `NUM_CLIENTS` and `MESSAGES_PER_CLIENT` in `config.py` (or via environment variables) to change the load.

---

## Error Handling

| Condition                  | Behaviour                                          |
|----------------------------|----------------------------------------------------|
| Duplicate username          | Server sends `ERROR|Username already taken`, closes connection |
| Username too long (>32 chars) | Server sends `ERROR|Username too long (max 32 chars)` |
| Unknown protocol command   | Server sends `ERROR|<description>` and continues  |
| Private message to offline user | Server sends `ERROR|User '<name>' not found`  |
| TLS handshake failure       | Server logs and closes the raw socket, loop continues |
| Abrupt client disconnect    | `handle_client` catches `ConnectionResetError`/`OSError`, cleans up rooms and registry |
| Partial file transfer       | `receive_file` raises `ConnectionError`; server logs and skips fan-out |

---

## Security Notes

- Certificates are self-signed and checked only by the client (`CERT_REQUIRED`). For production use, replace with a CA-signed certificate and enable `check_hostname = True`.
- The `server.key` file is committed to the repository for convenience in development. **Do not reuse it in production.**
- The server saves uploaded files to a local `received_files/` directory without sanitising the filename. Path traversal via `FILE|room|../../etc/passwd|0` is not prevented in the current implementation.

---

## Future Improvements

- GUI client (scaffolded in `client/client_gui.py`)
- Token-based authentication
- Message persistence (database backend)
- Filename sanitisation for file transfers
- Distributed / horizontally-scalable server
- End-to-end encryption (beyond transport TLS)
