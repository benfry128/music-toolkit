from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image
import io
import time

load_dotenv()
lastFMApiKey = os.getenv('LAST_FM_API_KEY')
spotifyID = os.getenv('SPOTIFY_CLIENT_ID')
spotifySecret = os.getenv('SPOTIFY_CLIENT_SECRET')


def printDict(d):
    for key in d.keys():
        print(f'{key}: {d[key]}')


def spotipySetup():
    scope = 'ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public  user-follow-modify user-follow-read user-read-playback-position user-top-read user-read-recently-played user-library-modify user-library-read user-read-email user-read-private'
    load_dotenv()
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotifyID,
                                                   client_secret=spotifySecret,
                                                   redirect_uri="http://localhost:1234",
                                                   scope=scope))
    return sp


def getRecentTracks(start_days_back, end_days_back, sp):
    all_recents = []

    for i in range(end_days_back, start_days_back + 1):
        startTime = int((time.time()-14400) / 86400) * 86400 + 14400 - (86400 * i)
        endTime = startTime + 86400

        r = requests.get(f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=benfry128&api_key={lastFMApiKey}&format=json&from={startTime}&to={endTime}&limit=200")
        recents = r.json()['recenttracks']['track']

        if type(recents) is dict:
            recents = [recents]

        if sp.current_playback()['is_playing']:
            del recents[0]  # every lastfm api call returns the currently playing track, so remove if currently playing

        print(f'Collecting lastfm data from {i} days back...Got {len(recents)} tracks')
        all_recents.extend(recents)

    return all_recents


def getAllPlaylists(user_id, sp):
    total_playlists = sp.user_playlists(user_id)['total']

    offset = 0
    playlists = []
    while offset < total_playlists:
        playlists.extend(sp.user_playlists(user_id)['items'])
        offset += 50

    return playlists


def getAllTracks(playlist_id, sp):
    print("Getting tracks 0-99")
    result = sp.playlist_tracks(playlist_id)
    total_tracks = result['total']

    offset = 100
    tracks = result['items']
    while offset < total_tracks:
        print(f"Getting tracks {offset}-{offset+99}")
        tracks.extend(sp.playlist_tracks(playlist_id, offset=offset)['items'])
        offset += 100

    print(f'Retrieved {len(tracks)}')

    print('Now digging through to find good versions')
    real_tracks = []
    for track in tracks:
        if not track['is_local'] and track['track'] and track['track']['type'] == 'track':
            if 'US' in track['track']['available_markets']:
                real_tracks.append(track['track'])
            else:
                alt = trackDownTrack(track['track'], sp)
                if alt:
                    real_tracks.append(alt)

    print(f'Finished, retrieved {len(real_tracks)} tracks in the end')
    return real_tracks


def trackDownTrack(track, sp):
    goodName = track['name'].lower()
    goodArtist = track['artists'][0]['name'].lower()
    isrc = track['external_ids']['isrc']

    good_tracks = sp.search(q=f'isrc:{isrc}', type='track')['tracks']['items']
    if good_tracks:
        return good_tracks[0]

    good_tracks = sp.search(q=f'track:{goodName} artist:{goodArtist}', type='track')['tracks']['items']
    if good_tracks:
        newName = good_tracks[0]['name'].lower()
        newArtist = good_tracks[0]['artists'][0]['name'].lower()

        if goodName == newName and goodArtist == newArtist:
            return good_tracks[0]
    return None


def compile_image(to_a_side, size, image_urls):
    bigImage = Image.new("RGB", (size * to_a_side, size * to_a_side))

    for id, url in enumerate(image_urls):
        print('Building image...')
        response = requests.get(url, stream=True)
        image = Image.open(io.BytesIO(response.content))
        x = (id % to_a_side) * size
        y = (id // to_a_side) * size
        bigImage.paste(image, (x, y))
        del image
        del response

    bigImage.show()
