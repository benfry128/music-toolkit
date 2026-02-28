import utils
import os
from pprint import pprint

sp = utils.spotipy_setup()

MY_USER_ID = os.getenv('ME_SPOTIFY_ID')

playlists = utils.get_all_playlists(MY_USER_ID, sp)

skip_playlists = ['Bangers', 'Vibes', 'Thonkers', 'Classics - Hi', 'Classics - Lo', 'To Listen', ]

artists = {}

for playlist in playlists:
    if playlist['collaborative'] or not playlist['owner']['id'] == MY_USER_ID or playlist['name'] in skip_playlists:
        print(f"{playlist['name']} EXCLUDED")
        continue
    analyze = input(f'Analyze playlist "{playlist['name']}"? (y/n/s to skip all) ')
    while analyze != 'y' and analyze != 'n' and analyze != 's':
        analyze = input(f'You idiot.\nAnalyze playlist "{playlist['name']}"? (y/n/s to skip all) ')

    if analyze == 's':
        break
    elif analyze == 'n':
        continue

    print(playlist['name'])
    tracks = utils.get_all_tracks(playlist['uri'], sp)
    for track in tracks:
        for artist in track['artists']:
            artist_uri = artist['uri']
            if artist_uri in artists:
                artists[artist_uri] += 1
            else:
                artists[artist_uri] = 1
    pprint(artists)

sorted_artists = sorted(artists, key=artists.get, reverse=True)

genres = {}

for artist_uri in sorted_artists:
    artist = sp.artist(artist_uri)
    print(f'{artist['name']} genres: {artist['genres']}')
    for genre in artist['genres']:
        if genre in genres:
            genres[genre].append(artist['name'])
        else:
            genres[genre] = [artist['name']]


def lengthGet(n):
    return len(genres[n])


sorted_genres = sorted(genres, key=lengthGet, reverse=True)

for genre in sorted_genres:
    print(f'{genre}: {genres[genre]}')
