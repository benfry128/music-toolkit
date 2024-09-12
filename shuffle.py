import random
import time
import utils

sp = utils.spotipy_setup()

startTime = int((time.time()-14400) / 86400) * 86400 - 72000
endTime = startTime + 86400

recents = utils.get_recent_tracks(1, 1, sp)

recentDict = {}
for recent in recents:
    recentDict[f'{recent['name']} {recent['artist']}'.lower()] = True

playlist_ids = [
    ["5Lh62TlIAUHgaFYo6IE2cZ", "1ciFrlllVeEBETOkvFn4qN"],  # bangers
    ["5MS4Z0D5HDugNZspLDs9uU", "6JJn8w2iqrxIFXUczrmT86"],  # thonkers
    ["42C2EObXUN25rSCzM99QTK", "1hNFjAax1k8n36HYIqT8V2"]   # vibes
]

for playlist_pair in playlist_ids:
    new_id = playlist_pair[1]

    playlist = sp.playlist(new_id)
    print(playlist['name'])

    tracks = utils.getAllTracks(new_id, sp)
    print(len(tracks))

    back_of_list = []
    front_of_list = []
    for track in tracks:
        trackName = track['name']
        trackArtist = track['artists'][0]['name']
        trackId = track['uri']
        if f'{trackName} {trackArtist}'.lower() in recentDict:
            print(trackName + " was in recents")
            back_of_list.append(trackId)
        else:
            front_of_list.append(trackId)

    front_len = len(front_of_list)
    front_front = front_of_list[:front_len // 2]
    front_back = front_of_list[front_len // 2:]

    random.shuffle(front_front)
    random.shuffle(back_of_list)

    front_front.extend(front_back)
    front_front.extend(back_of_list)

    if front_front:
        sp.playlist_replace_items(new_id, front_front[0:100])
        offset = 100
        while offset < len(front_front):
            sp.playlist_add_items(new_id, front_front[offset:offset+100])
            offset += 100
            print(f'readding tracks... offset is {offset}')
