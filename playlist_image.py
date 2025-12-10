import utils

sp = utils.spotipy_setup()

results = utils.get_all_tracks('https://open.spotify.com/playlist/1ciFrlllVeEBETOkvFn4qN?si=23930ee47fd34dac', sp)

albums = {}
for track in results:
    if track['album']['uri'] in albums:
        albums[track['album']['uri']] += 1
    else:
        albums[track['album']['uri']] = 1

sorted_albums = sorted(albums, key=albums.get, reverse=True)

to_a_side = 10000
while to_a_side * to_a_side > len(sorted_albums):
    to_a_side = int(input('How many across? '))

image_urls = []
for uri in sorted_albums[:(to_a_side * to_a_side)]:
    album = sp.album(uri)
    image_urls.append(album['images'][0]['url'])
    print(f"Got URL for {album['name']}")

utils.compile_square_image(to_a_side, to_a_side, 640, image_urls, 'playlist image heheh')
