import mysql.connector
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image

MYSQL_PWD = os.getenv('MYSQL_PWD')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

scope = 'ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public  user-follow-modify user-follow-read user-read-playback-position user-top-read user-read-recently-played user-library-modify user-library-read user-read-email user-read-private'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                               client_secret=SPOTIFY_CLIENT_SECRET,
                                               redirect_uri="http://localhost:1234",
                                               scope=scope),
                                               requests_timeout=10,
                                               retries=1)

db = mysql.connector.connect(
    host='localhost',
    user='root',
    password=MYSQL_PWD,
    database='albums'
)

cursor = db.cursor()
cursor.execute('SELECT * FROM albums where id in (283, 297, 298, 424, 495, 578, 664);')

albums = cursor.fetchall()

for album in albums:
    # image_url = album[3]

    # response = requests.get(image_url, stream=True)
    # image = Image.open(io.BytesIO(response.content))
    # image.save(f'assets/{album[0]}.jpg')

    # sp_album = sp.album(album[10])
    
    # cursor.execute('Update albums set image = %s where id = %s', [sp_album['images'][0]['url'], album[0]])
    # db.commit()
    # print(album[1])

    

    # name = album[1]

    # artist = album[2]

    # sp_albums = sp.search(q=f'album:{name} artist:{artist}', type='album', limit=10)['albu ms']['items']

    # album_id = None

    # for sp_album in sp_albums:
    #     if sp_album['name'].lower() == name.lower() and sp_album['artists'][0]['name'].lower() == artist.lower():
    #         album_id = sp_album['id']
    #         break
            
    # if not album_id:
    #     print(f'Looking for {name} by {artist}')
    #     for sp_album in sp_albums:
    #         print('')
    #         print(sp_album['name'])
    #         print(sp_album['artists'][0]['name'])
        
    #     i = input('')
    #     if len(i) == 1:
    #         album_id = sp_albums[int(i)]['id']
    #     else:
    #         album_id = i

    # if album_id:
    #     sp_album = sp.album(album_id)
        
    #     if sp_album['name'] != name and input(f'Keep name {sp_album['name']}'):
    #         cursor.execute('Update albums set name = %s where id = %s', [sp_album['name'], album[0]])

    #     if sp_album['artists'][0]['name'] != artist and input(f'Keep artist {sp_album['artists'][0]['name']}'):
    #         cursor.execute('Update albums set artist = %s where id = %s', [sp_album['artists'][0]['name'], album[0]])
    
    #     cursor.execute('Update albums set spotify_id = %s where id = %s', [album_id, album[0]])
    #     db.commit()
