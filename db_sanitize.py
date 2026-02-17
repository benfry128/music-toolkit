import utils
import json

VERBOSE = False

(db, cursor) = utils.db_setup()

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

d = json.loads(text)

unrelated_track_ids = d['non_dupe_track_ids']

print('Checking for duplicate tracks...')
cursor.execute('SELECT track, artist FROM all_urls GROUP BY track, artist HAVING COUNT(*) > 1;')
for track, artist in cursor.fetchall():
    cursor.execute('SELECT track_id, album FROM all_urls WHERE track = %s AND artist = %s', (track, artist))
    dupe_records = cursor.fetchall()
    if all([record[0] in unrelated_track_ids for record in dupe_records]):
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
        if track_id not in unrelated_track_ids:
            unrelated_track_ids.append(track_id)

d['non_dupe_track_ids'] = unrelated_track_ids

with open("db_sanitize_metadata.json", 'w', encoding='utf-8') as f:
    f.write(json.dumps(d, indent=4))