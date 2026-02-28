import utils
import random
import os
from datetime import datetime, timezone

sp = utils.spotipy_setup()

# SETTINGS
EXCLUDE_COLLAB_PLAYLISTS = True
EXCLUDE_OTHERS_PLAYLISTS = True
EXPLICIT_ALLOWED = True
MY_USER_ID = os.getenv('ME_SPOTIFY_ID')
USER_ID_INPUT = input('User id? ')
USER_ID = MY_USER_ID if USER_ID_INPUT == 'mine' else USER_ID_INPUT

playlists = utils.get_all_playlists(USER_ID, sp)

punctuation = '\'"()*&^%$#@!.,></?;:[]{}\\|-++_`~'
punctuation_list = list(punctuation)

letters = 'abcdefghijklmnopqrstuvwxyz'
letter_list = list(letters)
letter_dict = {}

for letter in letters:
    letter_dict[letter] = {}

all_playlists = False

for playlist in playlists:
    if (EXCLUDE_COLLAB_PLAYLISTS and playlist['collaborative']) or (EXCLUDE_OTHERS_PLAYLISTS and not playlist['owner']['id'] == USER_ID):
        print(f"{playlist['name']} EXCLUDED")
        continue
    if not all_playlists:
        read_playlist = input(f"Include playlist {playlist['name']}? (y/n/s to skip the rest/a to read the rest) ")
        if read_playlist == 's':
            break
        elif read_playlist == 'a':
            all_playlists = True
        elif read_playlist != 'y':
            continue
    print(playlist['name'])
    tracks = utils.get_all_tracks(playlist['uri'], sp)

    for track in tracks:
        if track['explicit'] and not EXPLICIT_ALLOWED:
            continue
        track_name = track['name']
        track_id = track['uri']
        first_letter = 0
        for character in track_name:
            if character.lower() in letter_list:
                first_letter = character.lower()
                break
            elif character not in punctuation_list:
                break
        if not first_letter:
            continue

        letter_dict[first_letter][track_id] = 1

# loop through letter dict to choose a song from

all_letters = True
for letter in letter_dict:
    if not letter_dict[letter].keys():
        all_letters = False
        break

final_uris = []

if all_letters or input("Playlist will not be complete, continue? (y/n) ") == 'y':
    for letter in letter_dict:
        uris = []

        for uri in letter_dict[letter]:
            uris.append(uri)
        if uris:
            final_uris.append(uris[random.randint(0, len(uris) - 1)])

    # @TODO 2026-03 API changes
    a_to_z_playlist = sp.user_playlist_create(MY_USER_ID, f'A to Z - {sp.user(USER_ID)['display_name']} - {datetime.now(tz=timezone.utc).strftime('%m/%d/%Y')}')

    result = sp.user_playlist_add_tracks(MY_USER_ID, a_to_z_playlist['uri'], final_uris)
