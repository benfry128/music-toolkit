import io
import mysql.connector
import os
import re
import requests
import spotipy
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from spotipy.oauth2 import SpotifyOAuth
import random

load_dotenv()
LAST_FM_API_KEY = os.getenv('LAST_FM_API_KEY')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
MYSQL_PWD = os.getenv('MYSQL_PWD')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')


def strip_str(string):
    return re.sub(r'\W+', '', string).lower()


def remove_apostrophe_and_percent(string):
    return re.sub("'|%", '', string).lower()


def iso_to_seconds(iso: str):
    trimmed_iso = iso[2:-1]
    split_iso = re.split('H|M', trimmed_iso)
    seconds = int(split_iso[-1])
    minutes = int(split_iso[-2]) if len(split_iso) > 1 else 0
    hours = int(split_iso[-3]) if len(split_iso) > 2 else 0

    return hours + 3600 + minutes * 60 + seconds + 1


def spotipy_setup():
    scope = 'ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public  user-follow-modify user-follow-read user-read-playback-position user-top-read user-read-recently-played user-library-modify user-library-read user-read-email user-read-private'
    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                                     client_secret=SPOTIFY_CLIENT_SECRET,
                                                     redirect_uri="http://localhost:1234",
                                                     scope=scope),
                           requests_timeout=10,
                           retries=1)


def db_setup():
    db = mysql.connector.connect(
        host='localhost',
        user='root',
        password=MYSQL_PWD,
        database='spotify_toolkit'
    )
    cursor = db.cursor()
    return (db, cursor)


def merge_tracks(good_track, bad_track, db, cursor):
    cursor.execute('select track, artist from `all` where track_id in (%s, %s)', (good_track, bad_track))

    [(name1, artist1), (name2, artist2)] = cursor.fetchall()

    if not input(f"About to merge {name1} by {artist1} with {name2} by {artist2}. Good?"):
        # move all scrobbles from bad to good
        cursor.execute(f'UPDATE scrobbles SET track_id = {good_track} WHERE track_id = {bad_track}')
        # move all lastfm str records from bad to good
        cursor.execute(f'UPDATE last_fm_str_tracks SET track_id = {good_track} WHERE track_id = {bad_track}')
        cursor.execute(f'DELETE FROM tracks_artists where track_id = {bad_track}')
        cursor.execute(f'DELETE FROM tracks WHERE id = {bad_track}')
        db.commit()


def delete_track(id, db, cursor):
    cursor.execute(f'DELETE FROM scrobbles WHERE track_id = {id}')
    cursor.execute(f'DELETE FROM last_fm_str_tracks WHERE track_id = {id}')
    cursor.execute(f'DELETE FROM tracks WHERE id = {id}')
    db.commit()


def get_scrobbles_from_date_range(start, end, cursor):
    cursor.execute('SELECT utc, au.track_id, artist_id, album_id, track, artist, album, track_url, artist_url, album_url, image_url '
                   'FROM scrobbles as s INNER JOIN all_urls as au ON au.track_id = s.track_id WHERE utc > %s AND utc < %s', (start, end))
    recents_dicts = [
        {
            'utc': r[0],
            'track_id': r[1],
            'artist_id': r[2],
            'album_id': r[3],
            'track': r[4],
            'artist': r[5],
            'album': r[6],
            'track_url': r[7],
            'artist_url': r[8],
            'album_url': r[9],
            'image_url': r[10]
        } for r in cursor.fetchall()
    ]
    return recents_dicts


def get_recent_tracks(days_ago_start, days_ago_end, cursor):
    now = int(datetime.now().timestamp())
    return get_scrobbles_from_date_range(now - days_ago_start * 86400, now - days_ago_end * 86400, cursor)


def get_all_playlists(user_id, sp):
    total_playlists = sp.user_playlists(user_id)['total']

    offset = 0
    playlists = []
    while offset < total_playlists:
        playlists.extend(sp.user_playlists(user_id)['items'])
        offset += 50

    return playlists


def get_all_tracks(playlist_id, sp, find_good_tracks=True):
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

    if not find_good_tracks:
        return tracks

    print('Now digging through to find good versions')
    real_tracks = []
    for track in tracks:
        if not track['is_local'] and track['track'] and track['track']['type'] == 'track':
            if 'US' in track['track']['available_markets']:
                real_tracks.append(track['track'])
            else:
                alt = track_down_track(track['track'], sp)
                if alt:
                    real_tracks.append(alt)

    print(f'Finished, retrieved {len(real_tracks)} tracks in the end')
    return real_tracks


def track_down_track(track, sp):
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


def compile_square_image(up_down, left_right, size, image_urls):
    bigImage = Image.new("RGB", (size * left_right, size * up_down))

    random.shuffle(image_urls)

    for id, url in enumerate(image_urls):
        print('Building image...')
        response = requests.get(url, stream=True)
        image = Image.open(io.BytesIO(response.content))
        image.thumbnail((size, size))
        x = (id % left_right) * size
        y = (id // left_right) * size
        bigImage.paste(image, (x, y))
        del image
        del response

    bigImage.save(image_urls[0][-15:] + ".png")
    input('Get the image if you want it')


def sp_tracks(sp, cursor):
    cursor.execute("select uri from tracks where source = 'sp';")

    tracks = [row[0] for row in cursor.fetchall()]
    sp_tracks = []

    for i in range(0, len(tracks), 50):
        sp_tracks.extend(sp.tracks(tracks[i:i+50])['tracks'])
        print(len(sp_tracks))

    return sp_tracks


def sp_albums(sp, cursor):
    cursor.execute("SELECT uri FROM albums where source = 'sp' and id < 20;")

    albums = [row[0] for row in cursor.fetchall()]
    sp_albums = []

    for i in range(0, len(albums), 20):
        sp_albums.extend(sp.albums(albums[i:i+20])['albums'])
        print(f'{len(sp_albums)} albums loaded from Spotify so far')

    return sp_albums


def album_explicit_and_few_artists(sp_album):
    tracks = sp_album['tracks']['items']
    tracks_explicit = bool([1 for track in tracks if track['explicit']])
    three_or_fewer_artists = len(set([track['artists'][0]['name'] for track in tracks])) <= 3

    return tracks_explicit and three_or_fewer_artists


def merge_albums(uris, sp, db, cursor):
    # code to merge 2 albums

    titles = []
    album_dicts = []
    ids = []

    for uri in uris:
        cursor.execute('SELECT id from albums where uri = %s', [uri])
        ids.append(cursor.fetchall()[0][0])

    for uri in uris:
        cursor.execute('SELECT * FROM tracks inner join albums on tracks.album_id = albums.id WHERE albums.uri = %s', [uri])
        titles.append([song[1] for song in cursor.fetchall()])
        tracks = sp.album_tracks(uri)['items']
        track_titles = [track['name'] for track in tracks]
        track_uris = [track['id'] for track in tracks]
        album_dicts.append(dict(zip(track_titles, track_uris)))

    for t in titles:
        for ti in t:
            print(ti)
    input('Do you need to go and merge some tracks first????')

    for uri, album_dict, s in zip(uris, album_dicts, titles):
        print(f"Let's see about this url: {uri}")
        print(f'We have {len(s)} tracks in the db related to this url')
        good = True
        for title_set in titles:
            for title in title_set:
                if title not in album_dict:
                    print(f"couldn't find {title}")
                    good = False
                    break
            if not good:
                break
        if good:
            print("OK THAT'S GOOD!")
        else:
            print("NAH DON'T USE THIS ONE PROB")

    i = input("Ok you want to do it? Choose the index of the album you want to keep, or press enter to skip")
    if i:
        index = int(i)
        good_id = ids[index]
        album_dict = album_dicts[index]
        del ids[index]
        del titles[index]
        for (id, title_set) in zip(ids, titles):
            for title in title_set:
                print(f'{good_id}, {album_dict[title]}, {title}, {id}')
                cursor.execute('UPDATE tracks SET album_id = %s, uri = %s where name = %s and album_id = %s', (good_id, album_dict[title], title, id))
                db.commit()


def compile_circle_image(size, image_urls_and_amounts, total):
    angle = 0
    big_image = Image.new('RGB', [size, size])

    for url, amount in image_urls_and_amounts:
        print('Building image...')
        response = requests.get(url, stream=True)
        image = Image.open(io.BytesIO(response.content))

        resized = image.resize((size, size))

        slice = Image.new('L', [size, size], 0)
        draw = ImageDraw.Draw(slice)
        draw.pieslice([(0, 0), (size, size)], angle, angle + amount * 360 / total, fill='white', outline='white')
        angle += amount * 360 / total

        big_image.paste(resized, mask=slice)

    big_image.show()
