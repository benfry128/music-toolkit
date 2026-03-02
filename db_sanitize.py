import utils
import json

VERBOSE = False
RECHECK = False

sp = utils.spotipy_setup()

(db, cursor) = utils.db_setup()

def change_singles_to_albums(album_start_id):
    cursor.execute('SELECT id, name from albums where type = "single" and source = "sp" and id > %s order by id', [album_start_id])

    albums = cursor.fetchall()

    for single_id, single_name in albums:
        print(single_id)
        print(single_name)
        cursor.execute('select track, artist, track_id from all_urls where album_id = %s', [single_id])
        tracks = cursor.fetchall()
        for (single_track, single_artist, single_track_id) in tracks:
            print(f'track: {single_track} artist: {single_artist}\n')
            possible_tracks = sp.search(q=f'track:{single_track} artist:{single_artist}', type='track', limit=10)['tracks']['items']
            skip = True
            for track in possible_tracks:
                if track['name'] == single_track:
                    if track['album']['album_type'] == 'album':
                        print(f"Track: {track['name']} Album {track['album']['name']}. url is {track['external_urls']['spotify']}")
                        print("This one is labeled as an album")
                        skip = False

                    if track['album']['name'] != single_name:
                        cursor.execute('select id from albums where uri = %s', [track['album']['id']])
                        if cursor.fetchall():
                            print(f"Track: {track['name']}. Album {track['album']['name']}. url is {track['external_urls']['spotify']}")
                            print("WE GOT A HIT IN THE DB THIS IS GOOD")
                            skip = False

            if skip:
                continue

            url = input('Which url?')

            if not url:
                continue

            good_track = sp.track(url)
            print(good_track)
            uri = good_track['id']

            cursor.execute('select id from tracks where uri = %s', [uri])
            old_record = cursor.fetchone()
            if old_record:
                utils.merge_tracks(old_record[0], single_track_id, db, cursor)
                continue

            album_uri = good_track['album']['id']

            cursor.execute('select id from albums where uri = %s', [album_uri])
            old_album = cursor.fetchone()
            if old_album:
                album_id = old_album[0]
            else:
                input(f"about to put in a new album: {good_track['album']['name']}")
                cursor.execute('INSERT INTO albums (uri, name, type, source, image) VALUES (%s, %s, %s, %s, %s)', (album_uri, good_track['album']['name'], good_track['album']['album_type'], 'sp', good_track['album']['images'][0]['url'][24:]))
                album_id = cursor.lastrowid

            cursor.execute('update tracks set uri = %s, album_id = %s where id = %s', (uri, album_id, single_track_id))
            db.commit()

    return albums[-1][0]

dupe_checks = ['''SELECT utc FROM
               (SELECT utc, track_id, 
               LEAD(track_id, 1, 0) OVER (ORDER BY utc) AS idAfter, 
               LAG(track_id, 1, 0) OVER (ORDER BY utc) AS idBefore, 
               (LAG(utc, 1, 0) OVER (ORDER BY utc) - utc) * -1 AS timeBefore 
               FROM scrobbles ORDER BY utc) t 
               WHERE (idBefore = track_id OR idAfter = track_id) AND timeBefore < 60 AND timeBefore > 0;''',
               '''SELECT utc FROM 
               (SELECT utc, track_id, 
               LEAD(track_id, 1, 0) OVER (ORDER BY utc) AS idAfter, 
               LAG(track_id, 1, 0) OVER (ORDER BY utc) AS idBefore, 
               LEAD(utc, 1, 0) OVER (ORDER BY utc) - utc AS timeAfter 
               FROM scrobbles ORDER BY utc) t 
               WHERE (idBefore = track_id OR idAfter = track_id) AND timeAfter < 60 AND timeAfter > 0;'''
               ]

print('Checking for duplicate scrobbles...')
for dupe_check in dupe_checks:
    cursor.execute(dupe_check)
    dupes = [record[0] for record in cursor.fetchall()]
    if dupes:
        if input(f'Delete {len(dupes)} duplicate scrobbles? Type anything to skip'):
            print("Skipped")
            continue
        cursor.execute(f'DELETE FROM scrobbles WHERE utc in ({str(dupes)[1:-1]})')
        db.commit()

with open('db_sanitize_metadata.json', encoding='utf-8') as f:
    text = f.read()

db_sanitize_metadata = json.loads(text)

non_dupe_track_ids = [] if RECHECK else db_sanitize_metadata['non_dupe_track_ids']

print('Checking for duplicate tracks...')
cursor.execute('SELECT track, artist FROM all_urls GROUP BY track, artist HAVING COUNT(*) > 1;')
for track, artist in cursor.fetchall():
    cursor.execute('SELECT track_id, album FROM all_urls WHERE track = %s AND artist = %s', (track, artist))
    dupe_records = cursor.fetchall()
    if all([record[0] in non_dupe_track_ids for record in dupe_records]):
        if VERBOSE:
            print(f'Skipping {track} by {artist}')
        continue

    print(f"Possible duplicate track: {track} by {artist}\nOptions:")
    for track_id, album in dupe_records:
        print(f"Id {track_id} from album '{album}'")

    keep_id = input("Which one would you like to keep? (0-indexed, enter to skip")
    if keep_id:
        good_track = dupe_records[int(keep_id)][0]
        del dupe_records[int(keep_id)]
        for dupe_record in dupe_records:
            utils.merge_tracks(good_track, dupe_record[0], db, cursor)
        continue

    for track_id, _ in dupe_records:
        if track_id not in non_dupe_track_ids:
            non_dupe_track_ids.append(track_id)

db_sanitize_metadata['non_dupe_track_ids'] = non_dupe_track_ids

print('Checking for duplicate/deluxe albums...')
cursor.execute('''select a1.id, a2.id, max(ar1.name), a1.name,  a2.name, a1.uri, a2.uri from albums a1
	join tracks t1 on t1.album_id = a1.id join tracks_artists ta1 on t1.id = ta1.track_id join artists ar1 on ar1.id = ta1.artist_id and ta1.main
	join albums a2 on (a1.name like concat(a2.name, '%') or a2.name like concat(a1.name, '%')) and a1.id > a2.id
	join tracks t2 on t2.album_id = a2.id join tracks_artists ta2 on t2.id = ta2.track_id join artists ar2 on ar2.id = ta2.artist_id and ta2.main
    group by a1.id, a1.name, a2.id, a2.name, a1.uri, a2.uri
    having max(ar1.name) = max(ar2.name)
    order by a1.name;''')

updated_non_dupe_album_ids = [] if RECHECK else db_sanitize_metadata['non_dupe_album_ids']

for album1_id, album2_id, artist, album1_name, album2_name, album1_uri, album2_uri in cursor.fetchall():
    if album1_id in db_sanitize_metadata['non_dupe_album_ids'] and album2_id in db_sanitize_metadata['non_dupe_album_ids']:
        if VERBOSE:
            print(f'\nSkipping {album1_name} and {album2_name} from {artist}')
        continue
    print(f'\nPossible duplicate albums from {artist}: {album1_name} and {album2_name}.\nUris are {album1_uri} and {album2_uri}')

    should_merge = input('Should these be merged? No input if no, input if yes.')
    if not should_merge:
        if album1_id not in updated_non_dupe_album_ids:
            updated_non_dupe_album_ids.append(album1_id)
        if album2_id not in updated_non_dupe_album_ids:
            updated_non_dupe_album_ids.append(album2_id)
        continue

    print()
    utils.merge_albums([album1_id, album2_id], sp, db, cursor)

updated_non_dupe_album_ids.sort()
db_sanitize_metadata['non_dupe_album_ids'] = updated_non_dupe_album_ids

db_sanitize_metadata['album_start_id'] = change_singles_to_albums(0 if RECHECK else db_sanitize_metadata['album_start_id'])

with open('db_sanitize_metadata.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(db_sanitize_metadata, indent=4))

cursor.execute('delete from albums where (select count(*) from tracks where album_id = albums.id) = 0;')
db.commit()