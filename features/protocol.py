# features/protocol.py
# Parses incoming raw messages into structured dictionaries based on command type.

def parse_message(data):
    # Splits incoming message into parts using '|' as delimiter.
    parts = data.strip().split("|")
    command = parts[0]

    if command == "JOIN":
        # Handles room join request.
        return {"type": "join", "room": parts[1]}

    elif command == "LEAVE":
        # Handles room leave request.
        return {"type": "leave", "room": parts[1]}

    elif command == "MSG":
        # Handles normal message sent to a room.
        return {
            "type": "message",
            "room": parts[1],
            "content": parts[2]
        }

    elif command == "PRIVATE":
        # Handles private message between users.
        return {
            "type": "private",
            "user": parts[1],
            "content": parts[2]
        }

    elif command == "FILE":
        # Handles file transfer request with metadata.
        return {
            "type": "file",
            "room": parts[1],
            "filename": parts[2],
            "size": int(parts[3])
        }

    else:
        # Handles unknown or unsupported commands.
        return {"type": "unknown"}
