def parse_message(data):

    parts = data.strip().split("|")
    command = parts[0]

    if command == "JOIN":
        return {"type": "join", "room": parts[1]}

    elif command == "LEAVE":
        return {"type": "leave", "room": parts[1]}

    elif command == "MSG":
        return {"type": "message", "room": parts[1], "content": parts[2]}

    elif command == "PRIVATE":
        return {"type": "private", "user": parts[1], "content": parts[2]}

    elif command == "FILE":
        return {
            "type": "file",
            "room": parts[1],
            "filename": parts[2],
            "size": int(parts[3])
        }

    else:
        return {"type": "unknown"}