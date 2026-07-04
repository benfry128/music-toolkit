import utils
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()
MYSQL_PWD = os.getenv('RDS_MYSQL_PWD')
(local_db, local_cursor) = utils.db_setup()
sp = utils.spotipy_setup()

albums_db = mysql.connector.connect(
    host='albums.c4hk40ksa2ki.us-east-1.rds.amazonaws.com',
    user='admin',
    password=MYSQL_PWD,
    database='albums'
)
albums_cursor = albums_db.cursor()

albums_cursor.execute('select spotify_id, title from albums where date_listened is not null and length(title) > 4;')

album_data = albums_cursor.fetchall()
reviewed_album_uris = [a[0] for a in album_data]
reviewed_album_names = [a[1] for a in album_data]

sql_text = ('select albums.uri, albums.name, count(tracks.id) '
             'from tracks join albums on tracks.album_id = albums.id '
             'where albums.source = \'sp\' '
             'group by album_id having count(tracks.id) > 10 '
             'order by count(tracks.id) desc;')

local_cursor.execute(sql_text)

listened_albums = [{'uri': a[0], 'title': a[1], 'tracks': a[2]} for a in local_cursor.fetchall()]
unlistened_albums = []

for listened_album in listened_albums:
    if listened_album['uri'] in reviewed_album_uris:
        continue
    accepted = False
    for name in reviewed_album_names:
        if listened_album['title'].lower() in name.lower() or name.lower() in listened_album['title'].lower():
            print(f'Looking for {listened_album['title']}...')
            accept = input(f'Is {name} the same thing? Type if not')
            if not accept:
                accepted = True
                break
    if accepted:
        continue
    print(listened_album['tracks'])
    unlistened_albums.append(f'{listened_album['tracks']} from {listened_album['title']}')

print(unlistened_albums)
