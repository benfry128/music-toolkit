import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()
lastFMApiKey = os.getenv('LAST_FM_API_KEY')
spotifyID = os.getenv('SPOTIFY_CLIENT_ID')
spotifySecret = os.getenv('SPOTIFY_CLIENT_SECRET')


def printDict(d):
    for key in d.keys():
        print(f'{key}: {d[key]}')


startTime = int((time.time()-14400) / 86400) * 86400 - 72000

endTime = startTime + 86400

r = requests.get(f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=benfry128&api_key={lastFMApiKey}&format=json&from={startTime}&to={endTime}&limit=200")

recents = r.json()['recenttracks']['track']

recentNameArtists = []
recentDict = {}
for recent in recents:
    # recentNameArtists.append(f'{recent['name']} {recent['artist']['#text']}')
    recentDict[f'{recent['name']} {recent['artist']['#text']}'.lower()] = True
    # print(f'{recent['name']} {recent['artist']['#text']}')
    
scope = 'user-library-read playlist-modify-public playlist-read-private'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotifyID,
                                               client_secret=spotifySecret,
                                               redirect_uri="http://localhost:1234",
                                               scope=scope))

playlist_ids = [
    ["5Lh62TlIAUHgaFYo6IE2cZ", "1ciFrlllVeEBETOkvFn4qN"],  # bangers
    ["5MS4Z0D5HDugNZspLDs9uU", "6JJn8w2iqrxIFXUczrmT86"],  # thonkers
    ["42C2EObXUN25rSCzM99QTK", "1hNFjAax1k8n36HYIqT8V2"]   # vibes
]

# for i in range(0, 50):
#    sp.playlist_add_items("1hNFjAax1k8n36HYIqT8V2", ['2YS7dyxfOw4ir5TX9USD7U', '2fkeWbM6iqTw7oGHTYm2lw', '2YS7dyxfOw4ir5TX9USD7U', '2fkeWbM6iqTw7oGHTYm2lw'])


for playlist_pair in playlist_ids:
    new_id = playlist_pair[1]

    playlist = sp.playlist(new_id)
    total_tracks = playlist['tracks']['total']
    print(playlist['name'])

    offset = 0
    tracks = []
    while offset < total_tracks:
        print(f"Getting tracks {offset}-{offset+99}")
        tracks.extend(sp.playlist_tracks(new_id, offset=offset)['items'])
        offset += 100
    print(len(tracks))

    back_of_list = []
    front_of_list = []
    for track in tracks:
        trackName = track['track']['name']
        trackArtist = track['track']['artists'][0]['name']
        trackId = track['track']['uri']
        # print(f'{trackName} {trackArtist}')
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
