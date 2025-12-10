import utils
from datetime import datetime

sp = utils.spotipy_setup()

(db, cursor) = utils.db_setup()

for i in range(1, 12):
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2025, 1, 1)

    start_timestamp = start_time.timestamp()
    end_timestamp = end_time.timestamp()

    cursor.execute('''
        select albums_url.image_url from scrobbles
            join tracks on tracks.id = scrobbles.track_id
            join albums_url on albums_url.id = tracks.album_id
        where utc > %s and utc < %s
        group by albums_url.id order by count(*) desc limit 36;
        ''', [start_timestamp, end_timestamp])

    album_info = [row[0] for row in cursor.fetchall()]

    utils.compile_square_image(3, 4, 640, album_info, f'Month {i}')
