# Multi-Room Secure Chat System with File Transfer

## 📌 Project Overview

This project implements a Secure Multi-Room Chat System using low-level TCP socket programming with SSL/TLS encryption.

The system supports:
- Multiple concurrent clients
- Multiple chat rooms
- Private messaging
- File sharing
- Guaranteed message ordering per room
- Performance evaluation under load

All communication occurs over secure TCP sockets using SSL.

---

## 🏗️ System Architecture

### Architecture Model

**Client–Server Architecture (Multi-Client)**
```
Clients  →  Secure TCP (SSL/TLS)  →  Central Chat Server
```

### Components

**1️⃣ Server**
- TCP socket creation
- SSL wrapping
- Concurrent client handling (threaded/async)
- Room management
- Message ordering
- File transfer handling

**2️⃣ Client**
- Secure SSL connection to server
- Command-line interface
- Join/leave rooms
- Send/receive messages
- File upload/download

---

## 🔐 Security

- SSL/TLS encryption for all communication
- Secure certificate-based authentication
- Handles SSL handshake failures gracefully

---

## 📡 Custom Application Protocol

All communication follows a structured application-layer protocol:
```
JOIN|room_name
LEAVE|room_name
MSG|room_name|message
PRIVATE|username|message
FILE|room_name|filename|filesize
```

This ensures clear parsing, command validation, and structured communication.

---

## 📂 Features

### ✅ Multi-Client Support
- Handles multiple concurrent clients
- Thread-safe shared resources

### ✅ Multi-Room Chat
- Dynamic room creation
- Room deletion when empty
- Room-specific broadcasting

### ✅ Message Ordering Guarantee
Each room maintains a sequence number:
```
[Room1][Seq:45] Hello Everyone
```
Ensures messages appear in correct order even under concurrency.

### ✅ Private Messaging
Send direct messages to specific users.

### ✅ File Transfer
- Metadata exchange before transfer
- Chunk-based streaming
- File reconstruction at client side
- Handles partial transfer errors

---

## ⚙️ Concurrency Model

- Thread-per-client model / Async I/O
- Proper synchronization using locks
- Handles abrupt client disconnections

---

## 📊 Performance Evaluation

Stress testing performed using simulated clients.

**Tests Conducted:** 10, 50, and 100 clients

**Metrics Measured:**
- Average response time
- Throughput (messages/sec)
- Latency
- Failure rate

**Observations:**
- Latency increases with number of clients
- SSL adds small encryption overhead
- System scales efficiently up to tested limit

---

## 🗂️ Project Structure
```
secure-multiroom-chat/
│
├── server/
│   ├── server.py
│   ├── connection_manager.py
│   ├── ssl_config.py
│
├── features/
│   ├── protocol.py
│   ├── rooms.py
│   ├── ordering.py
│   ├── file_transfer.py
│
├── client/
│   ├── client.py
│
├── load_test/
│   ├── stress_test.py
│
├── docs/
│   ├── architecture.png
│   ├── performance_graphs.png
│
├── README.md
└── requirements.txt
```

---

## 🚀 Setup Instructions

### 1️⃣ Clone Repository
```bash
git clone <repository_link>
cd secure-multiroom-chat
```

### 2️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Generate SSL Certificates
```bash
openssl req -new -x509 -days 365 -nodes -out server.crt -keyout server.key
```
Place certificates inside `server/ssl/`

### 4️⃣ Run Server
```bash
python server/server.py
```

### 5️⃣ Run Client
```bash
python client/client.py
```

---

## 🧪 Running Load Test
```bash
python load_test/stress_test.py
```

Configure the number of simulated clients inside the script.

---

## 🛠️ Error Handling

The system handles:
- Abrupt client disconnections
- Invalid protocol commands
- Duplicate usernames
- SSL handshake failures
- Partial file transfers
- Room not found errors

---

## 🎯 Learning Outcomes

This project demonstrates:
- Low-level TCP socket programming
- SSL/TLS secure communication
- Concurrency handling
- Custom protocol design
- File streaming over TCP
- Performance measurement and analysis

---

## 👨‍💻 Team Responsibilities

- Backend & SSL Implementation
- Protocol & Feature Development
- Client App & Performance Testing

---

## 📈 Future Improvements

- GUI-based client
- Database-backed message persistence
- Distributed server architecture
- Token-based authentication
- End-to-end encryption

---

## 📜 Conclusion

This project successfully implements a secure, scalable, and concurrent multi-room chat system using low-level socket programming concepts while maintaining message ordering and system stability under load.