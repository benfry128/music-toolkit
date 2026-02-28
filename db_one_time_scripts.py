import utils
from pprint import pprint
import requests
import os


def swap_out_clean_versions_of_albums(sp, db, cursor):
    cursor.execute("SELECT uri FROM albums where source = 'sp' and id < 20;")
    album_uris = [row[0] for row in cursor.fetchall()]

    for album_uri in album_uris:
        sp_album = sp.album(album_uri)
        if not utils.album_explicit_and_few_artists(sp_album):
            print(f'Album {sp_album['name']} is clean')
            title = sp_album['name']
            artist = sp_album['artists'][0]['name']
            other_versions = sp.search(f'album:{title} artist:{artist}', limit=5, type='album')['albums']['items']
            if type(other_versions) is list:
                for album in other_versions:
                    if not album['external_urls']['spotify'] == sp_album['external_urls']['spotify'] and album['name'] == sp_album['name']:
                        print(album['external_urls']['spotify'])
                        if not input('Maybe this one would be better?'):
                            cursor.execute('INSERT INTO albums (uri, name, type, source, image) VALUES (%s, %s, %s, %s, %s)', (album['id'], album['name'], album['album_type'], 'sp', album['images'][0]['url'][24:]))
                            # @TODO: fix so that this code updates track uris, not just album stuff
                            cursor.execute('update tracks set album = %s where album = %s', [album['external_urls']['spotify'], sp_album['external_urls']['spotify']])
                            db.commit()


def add_album_art(sp, db, cursor):
    cursor.execute("SELECT uri FROM albums where source = 'sp' and id < 20;")
    album_uris = [row[0] for row in cursor.fetchall()]

    for album_uri in album_uris:
        sp_album = sp.album(album_uri)
        cursor.execute('update albums set image = %s where uri = %s', [sp_album['images'][0]['url'], sp_album['id']])

    db.commit()

    cursor.execute('SELECT id, url FROM albums WHERE url like "%youtu.be%"')
    rows = cursor.fetchall()

    THUMBNAIL_SIZES = ['maxres', 'standard', 'high', 'medium', 'default']

    for row in rows:
        db_id = row[0]
        yt_id = row[1][17:]
        r = requests.get(f'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={yt_id}&key={utils.YOUTUBE_API_KEY}')
        pprint(r.json())
        thumbnails = r.json()['items'][0]['snippet']['thumbnails']
        for size in THUMBNAIL_SIZES:
            if size in thumbnails:
                cursor.execute('UPDATE albums SET image = %s where id = %s', [thumbnails[size]['url'], db_id])
                db.commit()
                break

    cursor.execute('SELECT id, url FROM albums WHERE url like "%youtube.com/playlist%"')
    rows = cursor.fetchall()

    for row in rows:
        db_id = row[0]
        yt_id = row[1][38:]
        r = requests.get(f'https://www.googleapis.com/youtube/v3/playlists?part=snippet&id={yt_id}&key={utils.YOUTUBE_API_KEY}')
        thumbnails = r.json()['items'][0]['snippet']['thumbnails']
        for size in THUMBNAIL_SIZES:
            if size in thumbnails:
                cursor.execute('UPDATE albums SET image = %s where id = %s', [thumbnails[size]['url'], db_id])
                db.commit()
                break


def merge_carriage_return_albums(db, cursor):
    cursor.execute("SELECT * FROM albums where uri like '%\r';")

    albums = cursor.fetchall()

    for album in albums:
        # print(album)
        cursor.execute('Select * from albums where uri = %s', [album[1][:-1]])
        real = cursor.fetchall()[0]
        cursor.execute('update tracks set album_id = %s where album_id = %s', [real[0], album[0]])

        print(real)
        # if album[1][-1] == '\r':
        #     print(album[1])
        #     input("HI")
        #     cursor.execute('update albums set uri = %s where uri = %s', [album[1][:-1], album[1]])
    db.commit()


def remove_unneeded_uri_info(db, cursor):
    cursor.execute("select * from tracks where source = 'yt' and (uri like '%&pp%' or uri like '%&list%');")
    tracks = cursor.fetchall()

    for track in tracks:
        uri = track[3]
        index = uri.find('&')
        new_uri = uri[:index]
        cursor.execute('update tracks set uri = %s where uri = %s', [new_uri, uri])
        db.commit()

    print(len(tracks))


# bad version of swap_out_clean_versions_of_albums above caused album uris to change without updating their constituent track uris, this code fixes it
def fix_track_uris_to_match_album_uris(sp, cursor, db):
    cursor.execute("SELECT tracks.id, tracks.uri, albums.uri, tracks.name, albums.name, albums.id FROM tracks join albums on tracks.album_id = albums.id where tracks.source = 'sp';")
    data = cursor.fetchall()

    for album_id in [3194]:
        print(album_id)
        db_album_tracks = [t for t in data if t[5] == album_id]
        if not db_album_tracks:
            continue
        sp_tracks = sp.tracks([record[1] for record in db_album_tracks])['tracks']
        fine = True
        for t in sp_tracks:
            print(t)
        for i in range(len(db_album_tracks)):
            if db_album_tracks[i][2] != sp_tracks[i]['album']['id']:
                fine = False
        if fine:
            continue
        print([t[3] for t in db_album_tracks])
        possible_albums = []
        for t in db_album_tracks:
            if t[2] not in possible_albums:
                possible_albums.append(t[2])
        for t in sp_tracks:
            if t['album']['id'] not in possible_albums:
                possible_albums.append(t['album']['id'])
        for a in possible_albums:
            print(f'https://open.spotify.com/album/{a}')
        chosen_album_uri = possible_albums[int(input('Which?'))]
        if not chosen_album_uri:
            continue
        chosen_album = sp.album(chosen_album_uri)
        chosen_album_tracks = sp.album_tracks(chosen_album_uri)['items']
        for t in db_album_tracks:
            sp_track = [spt for spt in chosen_album_tracks if spt['name'] == t[3]]
            if sp_track:
                sp_uri = sp_track[0]['id']
            else:
                sp_uri = input(f'URI for {t[3]}')
            sp_track = sp.track(sp_uri)
            cursor.execute('update tracks set uri = %s, name = %s where id = %s', [sp_uri, sp_track['name'], t[0]])
        cursor.execute('update albums set uri = %s, image = %s, type = %s where id = %s;',
                       [chosen_album_uri, chosen_album['images'][0]['url'][24:], chosen_album['album_type'], album_id])
        db.commit()


def find_old_songs(sp, cursor, db):
    MY_USER_ID = os.getenv('ME_SPOTIFY_ID')
    playlists = utils.get_all_playlists(MY_USER_ID, sp)

    for playlist in playlists:
        if playlist['collaborative'] or not playlist['owner']['id'] == MY_USER_ID:
            continue

        tracks = utils.get_all_tracks(playlist['uri'], sp, False)
        input(playlist['name'])
        for track in tracks:
            if int(track['added_at'][:4]) < 2024:
                cursor.execute('update tracks set old = 1 where uri = %s', [track['track']['id']])
                if cursor.rowcount != 1:
                    cursor.execute('select track_id from all_urls where track = %s and artist = %s',
                                   [track['track']['name'], track['track']['artists'][0]['name']])

                    ids = cursor.fetchall()
                    if len(ids) == 1:
                        cursor.execute('update tracks set old = 1 where id = %s', [ids[0][0]])

            db.commit()

    cursor.execute('select track_id, track, artist, album from all_urls where track_id > 4685 and not old order by track_id;')
    tracks = cursor.fetchall()
    for (id, track, artist, album) in tracks:
        x = input(f'{id}:\n{track}\n{artist}\n{album}')
        if x:
            cursor.execute('update tracks set old = 1 where id = %s;', [id])
            db.commit()


sp = utils.spotipy_setup()

db, cursor = utils.db_setup()

find_old_songs(sp, cursor, db)
