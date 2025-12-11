import utils
from datetime import datetime

sp = utils.spotipy_setup()

(db, cursor) = utils.db_setup()

year = 2025

for i in range(1, 13):
    start_time = datetime(year, i, 1)
    end_time = datetime(year + int(i == 12), i * int(i != 12) + 1, 1)
    if i == 12:
        end_time = datetime(year + 1, 1, 1)

    cursor.execute('''
        select image_url from all_scrobbles
        where scrobble_time >= %s and scrobble_time < %s
        group by image_url order by sum(runtime) desc limit 12;
        ''', [start_time, end_time])

    album_info = [row[0] for row in cursor.fetchall()]

    utils.compile_square_image(3, 4, 640, album_info, f'Year {year} month {i}')

# one yearly photo
start_time = datetime(year, 1, 1)
end_time = datetime(year + 1, 1, 1)

cursor.execute('''
    select image_url from all_scrobbles
    where scrobble_time >= %s and scrobble_time < %s
    group by image_url order by sum(runtime) desc limit 36;
    ''', [start_time, end_time])

album_info = [row[0] for row in cursor.fetchall()]

utils.compile_square_image(6, 6, 640, album_info, f'Year {year}')
