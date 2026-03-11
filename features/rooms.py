rooms = {}


def create_room(room_name):

    if room_name not in rooms:
        rooms[room_name] = {
            "clients": [],
            "sequence": 0
        }


def join_room(client, room_name):

    if room_name not in rooms:
        create_room(room_name)

    rooms[room_name]["clients"].append(client)


def leave_room(client, room_name):

    if room_name in rooms:

        if client in rooms[room_name]["clients"]:
            rooms[room_name]["clients"].remove(client)

        if len(rooms[room_name]["clients"]) == 0:
            del rooms[room_name]


def get_clients(room_name):

    if room_name in rooms:
        return rooms[room_name]["clients"]

    return []