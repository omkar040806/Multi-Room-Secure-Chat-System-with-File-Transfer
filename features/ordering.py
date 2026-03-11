from rooms import rooms


def get_next_sequence(room):

    if room not in rooms:
        return 0

    rooms[room]["sequence"] += 1
    return rooms[room]["sequence"]


def attach_sequence(room, message):

    seq = get_next_sequence(room)

    formatted_message = f"[{room}][{seq}] {message}"

    return formatted_message