# features/ordering.py
# Adds ordered sequence numbers to messages using thread-safe sequence generation per room.

from features.rooms import get_next_sequence


def attach_sequence(room: str, message: str) -> str:
    # Generates next sequence number for the room and prefixes it to the message.
    seq = get_next_sequence(room)
    return f"[{room}][{seq}] {message}"
