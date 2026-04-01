# features/ordering.py
from features.rooms import get_next_sequence


def attach_sequence(room: str, message: str) -> str:
    seq = get_next_sequence(room)
    return f"[{room}][{seq}] {message}"
