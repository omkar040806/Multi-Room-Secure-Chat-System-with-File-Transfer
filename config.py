# config.py  —  single source of truth for the whole project
import os

# Network 
HOST = os.getenv("CHAT_HOST", "0.0.0.0")
SERVER_IP = os.getenv("CHAT_SERVER_IP", "127.0.0.1")   # clients connect here
PORT = int(os.getenv("CHAT_PORT", 5000))

# TLS 
CERT = os.getenv("CHAT_CERT", "ssl/server.crt")
KEY = os.getenv("CHAT_KEY",  "ssl/server.key")

# Buffers
BUFFER_SIZE = 4096

# Stress-test defaults
NUM_CLIENTS = 20
MESSAGES_PER_CLIENT = 20
