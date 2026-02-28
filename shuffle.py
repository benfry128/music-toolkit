import random
import utils

sp = utils.spotipy_setup()
db, cursor = utils.db_setup()

recents = utils.get_recent_tracks(1, 0, cursor)

recent_dict = {}
for recent in recents:
    recent_dict[f'{recent['track']} {recent['artist']}'.lower()] = True

playlist_ids = [
    ["5Lh62TlIAUHgaFYo6IE2cZ", "1ciFrlllVeEBETOkvFn4qN"],  # bangers
    ["5MS4Z0D5HDugNZspLDs9uU", "6JJn8w2iqrxIFXUczrmT86"],  # thonkers
    ["42C2EObXUN25rSCzM99QTK", "1hNFjAax1k8n36HYIqT8V2"]   # vibes
]

for old_id, new_id in playlist_ids:
    # @TODO: 2026-03 API changes
    playlist = sp.playlist(new_id)
    print(playlist['name'])

    tracks = utils.get_all_tracks(new_id, sp)
    print(len(tracks))

    back_of_list = []
    front_of_list = []
    for track in tracks:
        track_name = track['name']
        track_artist = track['artists'][0]['name']
        track_uri = track['uri']
        if f'{track_name} {track_artist}'.lower() in recent_dict:
            print(track_name + " was in recents")
            back_of_list.append(track_uri)
        else:
            front_of_list.append(track_uri)

    front_len = len(front_of_list)
    front_front = front_of_list[:front_len // 2]
    front_back = front_of_list[front_len // 2:]

    random.shuffle(front_front)
    random.shuffle(back_of_list)

    front_front.extend(front_back)
    front_front.extend(back_of_list)

    if front_front:
        # @TODO: 2026-03 API changes
        sp.playlist_replace_items(new_id, front_front[0:100])
        offset = 100
        while offset < len(front_front):
            # @TODO: 2026-03 API changes
            sp.playlist_add_items(new_id, front_front[offset:offset+100])
            offset += 100
            print(f'readding tracks... offset is {offset}')
