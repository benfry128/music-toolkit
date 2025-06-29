import utils
from datetime import datetime
from pprint import pprint

sp = utils.spotipy_setup()

db, cursor = utils.db_setup()

print(sp.album('42oQv8fbI5CbeuAasf2ILC')['images'])

# cursor.execute('''select count(utc), image from
# scrobbles join track_album_main_artist on scrobbles.track_id = track_album_main_artist.track_id
# join albums on track_album_main_artist.album_id = albums.id
# where not image = '' and artist not in ('Mikel', 'Helynt', 'Besso0', 'Amos Roddy',
# 'Joris de Man', 'Lena Raine', 'Andrew Prahlow', 'GENTLE LOVE',
# 'Slofi', 'ImRuscelOfficial', 'The Flight')
# group by artist, album, image order by count(utc) desc limit 250;
# ''')
# results = [{'count': row[0], 'url': row[1]} for row in cursor.fetchall()]

# urls = []
# for result in results:
#     urls.extend([result['url']] * int(result['count'] / 20))
# urls = urls[0:225]
# random.shuffle(urls)

# utils.compile_square_image(15, 80, urls)

# db_one_time_scripts.add_album_art(sp, db, cursor)

# utils.compile_circle_image(1000, ['https://i.scdn.co/image/ab67616d0000b273f38c6b37a21334e22005b1f7',
#                                   'https://i.scdn.co/image/ab67616d0000b2737d92a7b081f16384dfc13464',
#                                   'https://i.scdn.co/image/ab67616d0000b2735b96a8c5d61be8878452f8f1',
#                                   'https://i.scdn.co/image/ab67616d0000b2739a7c3dd5910b43e1f16c9ad1'
#                                   ])


# @TODO: add function to get db records from a specific date period
# @TODO: update compile_circle_image to handle different size slices

# d = datetime(2024, 1, 1).timestamp()
# d2 = datetime.now().timestamp()

# scrobbles = utils.get_scrobbles_from_date_range(d, d2, cursor)
# num_of_scrobbles = len(scrobbles)
# art_dict = {}


# for s in scrobbles:
#     if s['image_url'] not in art_dict:
#         art_dict[s['image_url']] = 1
#     else:
#         art_dict[s['image_url']] += 1

# art_list = list(art_dict.items())

# art_list.sort(key=lambda x: x[1], reverse=True)

# id_to_stop_at = None
# for id, art in enumerate(art_list):
#     if art[1] < num_of_scrobbles / 100:
#         id_to_stop_at = id
#         break

# if id_to_stop_at:
#     art_list = art_list[:id_to_stop_at]

# pprint(art_list)
# input("HI")

# utils.compile_circle_image(1000, art_list, num_of_scrobbles)

