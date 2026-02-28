import random
import utils

sp = utils.spotipy_setup()

playlist_ids = [
    ["5Lh62TlIAUHgaFYo6IE2cZ", "1ciFrlllVeEBETOkvFn4qN"],  # bangers
    ["5MS4Z0D5HDugNZspLDs9uU", "6JJn8w2iqrxIFXUczrmT86"],  # thonkers
    ["42C2EObXUN25rSCzM99QTK", "1hNFjAax1k8n36HYIqT8V2"]   # vibes
]

for old_id, new_id in playlist_ids:
    uris = [track['uri'] for track in utils.get_all_tracks(old_id, sp)]

    random.shuffle(uris)

    # @TODO: 2026-03 API changes
    sp.playlist_replace_items(new_id, uris[0:100])
    offset = 100
    while offset < len(uris):
        sp.playlist_add_items(new_id, uris[offset:offset+100])
        offset += 100
