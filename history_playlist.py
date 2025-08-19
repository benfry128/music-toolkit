from datetime import datetime
import os
import utils

MY_USER_ID = os.getenv('ME_SPOTIFY_ID')

sp = utils.spotipy_setup()
(db, cursor) = utils.db_setup()

start_time = [int(t) for t in input('Start time: (YYYY-MM-DD-HH-MM-SS)').split('-')]
end_time = [int(t) for t in input('End time: (YYYY-MM-DD-HH-MM-SS)').split('-')]

start = datetime(start_time[0], start_time[1], start_time[2], start_time[3], start_time[4], start_time[5])
end = datetime(end_time[0], end_time[1], end_time[2], end_time[3], end_time[4], end_time[5])

cursor.execute('''
    select uri from scrobbles
        join tracks on tracks.id = scrobbles.track_id
    where utc > %s and utc < %s and source = 'sp';
    ''', [start.timestamp(), end.timestamp()])

uris = [row[0] for row in cursor.fetchall()]
sp_tracks = []

print(start.date())

a_to_z_playlist = sp.user_playlist_create(MY_USER_ID, f'Listened from {start} to {end}')

for i in range(0, len(uris), 50):
    sp.user_playlist_add_tracks(MY_USER_ID, a_to_z_playlist['uri'], uris[i:i + 50])
