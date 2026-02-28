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

    return hours * 3600 + minutes * 60 + seconds + 1


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
    return db, cursor


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
    print("Getting tracks 0-49")
    result = sp.playlist_items(playlist_id, additional_types=('track',))

    total_tracks = result['total']

    offset = 50
    tracks = result['items']
    while offset < total_tracks:
        print(f"Getting tracks {offset}-{offset+49}")
        tracks.extend(sp.playlist_items(playlist_id, additional_types=('track',), offset=offset)['items'])
        offset += 50

    print(f'Retrieved {len(tracks)}')

    # @TODO: Check if this track type check is necessary now that additional_types=('track',) is above
    return [t['track'] for t in tracks if not t['is_local'] and t['track'] and t['track']['type'] == 'track'] if find_good_tracks else tracks


def compile_square_image(up_down, left_right, size, image_urls, file_name):
    bigImage = Image.new("RGB", (size * left_right, size * up_down))

    random.shuffle(image_urls)

    for id, url in enumerate(image_urls):
        print('Building image...')
        response = requests.get(url, stream=True)
        image = Image.open(io.BytesIO(response.content))
        image.thumbnail((size, size))
        width, height = image.size
        x = (id % left_right) * size + (size - width) // 2
        y = (id // left_right) * size + (size - height) // 2
        bigImage.paste(image, (x, y))
        del image
        del response

    bigImage.save(f"{file_name}.png")


def get_sp_tracks(sp, cursor):
    cursor.execute("select uri from tracks where source = 'sp';")

    tracks = [row[0] for row in cursor.fetchall()]
    sp_tracks = []

    for i in range(0, len(tracks), 50):
        sp_tracks.extend(sp.tracks(tracks[i:i+50])['tracks'])
        print(len(sp_tracks))

    return sp_tracks


def album_explicit_and_few_artists(sp_album):
    tracks = sp_album['tracks']['items']
    tracks_explicit = bool([1 for track in tracks if track['explicit']])
    three_or_fewer_artists = len(set([track['artists'][0]['name'] for track in tracks])) <= 3

    return tracks_explicit and three_or_fewer_artists


def merge_albums(album_ids, sp, db, cursor):
    # code to merge 2 albums
    album_dicts = []
    all_db_tracks = []

    for album_id in album_ids:
        cursor.execute('SELECT uri, name from albums WHERE id = %s', [album_id])
        db_album = cursor.fetchall()[0]
        sp_tracks = sp.album_tracks(db_album[0])['items']
        title = db_album[1]
        cursor.execute('SELECT name, id FROM tracks WHERE album_id = %s', [album_id])
        db_tracks = cursor.fetchall()
        all_db_tracks.extend(db_tracks)
        album_dicts.append({
            'id': album_id,
            'title': title,
            'db_tracks': db_tracks,
            'sp_uris_by_title': {track['name']: track['id'] for track in sp_tracks}
        })

    all_db_tracks.sort()
    print('Full list of track titles:')
    for db_track in all_db_tracks:
        print(f'{db_track[0]} - {db_track[1]}')

    while True:
        merge_data = input('Merge tracks? Input as "[track_id_to_keep],[track_id_to_delete]"')
        if not merge_data:
            break
        merge_targets = merge_data.split(',')
        merge_tracks(merge_targets[0], merge_targets[1], db, cursor)

    print('\nAlbum summaries:')

    for album_dict in album_dicts:
        print(f"\n{album_dict['title']} - {album_dict['id']}")
        print(f'This album has {len(album_dict['db_tracks'])} db tracks')
        good = True
        for db_track in all_db_tracks:
            if db_track[0] not in album_dict['sp_uris_by_title']:
                print(f"Couldn't find {db_track[0]}")
                good = False
        if good:
            print("Found all tracks")

    i = input("\nContinue merge? Choose the index of the album to keep, or enter to skip:")
    if not i:
        return

    index = int(i)
    good_album_dict = album_dicts[index]
    for album_dict in album_dicts:
        if album_dict['id'] == good_album_dict['id']:
            continue
        for track in album_dict['db_tracks']:
            print(f'Updating {track[0]}')
            cursor.execute('UPDATE tracks SET album_id = %s, uri = %s where id = %s', (good_album_dict['id'], good_album_dict['sp_uris_by_title'][track[0]], track[1]))
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
