import json
from datetime import datetime
import utils
import db_update

f = open('Streaming_History_Audio_2023-2024_2.json', encoding='utf-8')

text = f.read()

d = json.loads(text)

last = None

dedupe = []

(db, cursor) = utils.db_setup()

sp = utils.spotipy_setup()

for i in d:
    if last:
        if i['spotify_track_uri'] == last['spotify_track_uri']:
            last['ms_played'] += i['ms_played']
        else:
            if last['ms_played'] > 30000 and last['master_metadata_track_name']:
                dedupe.append(last)
    last = i

time_format_data = '%Y-%m-%dT%H:%M:%SZ'

last_added_utc = 0

cursor.execute('select max(utc) from scrobbles where utc < 1704178395;')
earliest_utc = cursor.fetchall()[0][0]

for scrobble in dedupe:
    uri = scrobble['spotify_track_uri'].split(':')[2]

    if scrobble['offline_timestamp'] is not None and scrobble['offline']:
        timestamp = scrobble['offline_timestamp'] if scrobble['offline_timestamp'] < 100000000000 else scrobble['offline_timestamp'] // 1000
    else:
        timestamp = datetime.strptime(scrobble['ts'], time_format_data).timestamp()

    if timestamp <= earliest_utc or timestamp > 1704178395:
        continue

    if timestamp == last_added_utc:
        timestamp = last_added_utc + 1

    cursor.execute('select id from tracks where uri = %s', [uri])
    results = cursor.fetchall()
    if results:
        print(results[0][0])
        cursor.execute('INSERT INTO scrobbles (utc, track_id) VALUES (%s, %s)', (timestamp, results[0][0]))
        last_added_utc = timestamp
        db.commit()
        continue

    artist = scrobble['master_metadata_album_artist_name']
    album = scrobble['master_metadata_album_album_name']
    title = scrobble['master_metadata_track_name']

    db_update.process_track(timestamp, artist, album, title, db, cursor, sp)
    last_added_utc = timestamp
