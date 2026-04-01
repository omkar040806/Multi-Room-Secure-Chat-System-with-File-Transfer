# features/rooms.py
import threading

# Manages chat rooms, clients in each room, and message ordering
# Each room stores its clients and a sequence counter for ordering messages

# rooms[name] = {"clients": [...], "sequence": int, "seq_lock": Lock}
rooms: dict = {}
_rooms_lock = threading.Lock()  # Lock to ensure thread-safe access to the rooms dictionary


def _make_room(name: str) -> dict:
    # Creates a new room with empty client list and sequence counter
    return {"clients": [], "sequence": 0, "seq_lock": threading.Lock()}


def join_room(client, room_name: str) -> None:
    # Adds a client to a room (creates room if it doesn't exist)
    # Ensures no duplicate clients are added
    with _rooms_lock:
        if room_name not in rooms:
            rooms[room_name] = _make_room(room_name)
        if client not in rooms[room_name]["clients"]:
            rooms[room_name]["clients"].append(client)


def leave_room(client, room_name: str) -> None:
    # Removes a client from a room
    # Deletes the room if it becomes empty
    with _rooms_lock:
        if room_name not in rooms:
            return
        try:
            rooms[room_name]["clients"].remove(client)
        except ValueError:
            pass  # client was already gone — harmless
        if not rooms[room_name]["clients"]:
            del rooms[room_name]


def get_clients(room_name: str) -> list:
    # Returns list of clients in a given room
    with _rooms_lock:
        if room_name in rooms:
            return list(rooms[room_name]["clients"])
        return []


def get_next_sequence(room_name: str) -> int:
    # Generates next sequence number for messages in a room
    # Ensures messages are ordered correctly using thread-safe locking
    """Thread-safe per-room sequence counter."""
    with _rooms_lock:
        if room_name not in rooms:
            return 0
        room = rooms[room_name]

    # Fine-grained lock so rooms don't block each other
    with room["seq_lock"]:
        room["sequence"] += 1
        return room["sequence"]
