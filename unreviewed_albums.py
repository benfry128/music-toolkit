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

albums_cursor.execute('select spotify_id from albums where date_listened is not null;')

reviewed_album_uris = [a[0] for a in albums_cursor.fetchall()]

sql_text = ('select albums.uri, count(tracks.id) '
             'from tracks join albums on tracks.album_id = albums.id '
             'where albums.source = \'sp\' '
             'group by album_id having count(tracks.id) > 3 '
             'order by count(tracks.id) desc;')

local_cursor.execute(sql_text)

listened_albums = [{'uri': a[0], 'tracks': a[1]} for a in local_cursor.fetchall()]

for listened_album in listened_albums:
    if listened_album['uri'] not in reviewed_album_uris:
        sp_album = sp.album(listened_album['uri'])
        print(f'{listened_album['tracks']} listened from {sp_album['name']} by {sp_album["artists"][0]["name"]}')