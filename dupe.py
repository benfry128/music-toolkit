import random
import utils

scope = 'playlist-modify-public'

sp = utils.spotipySetup(scope)

playlist_ids = [
    ["5Lh62TlIAUHgaFYo6IE2cZ", "1ciFrlllVeEBETOkvFn4qN"],  # bangers
    ["5MS4Z0D5HDugNZspLDs9uU", "6JJn8w2iqrxIFXUczrmT86"],  # thonkers
    ["42C2EObXUN25rSCzM99QTK", "1hNFjAax1k8n36HYIqT8V2"]   # vibes
]

for pair in playlist_ids:
    old_id = pair[0]
    new_id = pair[1]

    tracks = utils.getAllTracks(old_id, sp)

    trackIds = []
    for track in tracks:
        trackId = track['uri']
        trackIds.append(trackId)

    random.shuffle(trackIds)

    sp.playlist_replace_items(new_id, trackIds[0:100])
    offset = 100
    while offset < len(trackIds):
        sp.playlist_add_items(new_id, trackIds[offset:offset+100])
        offset += 100
