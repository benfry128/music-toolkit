import time
import requests
from utils import album_explicit_and_few_artists, db_setup, iso_to_seconds, LAST_FM_API_KEY, remove_apostrophe_and_percent, spotipy_setup, strip_str, YOUTUBE_API_KEY
from datetime import datetime

sp = spotipy_setup()

(db, cursor) = db_setup()

SEARCH_PRIORITIES = [
    lambda track: 'sp' + track['album']['id'] in album_uri_matches,
    lambda track: track['explicit'] and track['album']['album_type'] == 'album',
    lambda track: album_explicit_and_few_artists(sp.album(track['album']['id'])) and track['album']['album_type'] == 'album',
    lambda track: track['explicit'],
    lambda track: album_explicit_and_few_artists(sp.album(track['album']['id'])),
    lambda _: True,
]

POKEMON_ARTIST_URIS = {
    'Hitomi Sato': '6ogSS7KK79OuXaPIOcT2qW',
    'Morikazu Aoki': '7aTFMiBdrwAWYhcQ3PWnAZ',
    'Go Ichinose': '2XhZz8Jf1MrQqmdL5RuTlK',
    'Junichi Masuda': '4VIuhf1E0e1gwkftD5VSXr',
}


def search_spotify_tracks(sp_tracks, bridge_codes):
    for prio in SEARCH_PRIORITIES:
        for sp_track in sp_tracks:
            if prio(sp_track):
                if strip_str(sp_track['name'] + sp_track['artists'][0]['name'] + sp_track['album']['name']) in bridge_codes:
                    return sp_track
                i = input(f'Is this ok? {sp_track['name']} by {sp_track['artists'][0]['name']} off of {sp_track['album']['name']}')
                if not i:
                    return sp_track
                if i == 'b':
                    break
                if i == 's':
                    return None
    return None


def get_artist_object(artist_name):
    cursor.execute('SELECT uri, source FROM artists WHERE name = %s', [artist_name])
    results = cursor.fetchone()
    if results:
        print(f"Found a possible match in the db, source is {results[1]}")
    artist_url = input(f"Channel ID or spotify URL for {artist_name}? ")
    if artist_url:
        artist_uri = artist_url[0 if artist_url[0] == 'U' else 32:]
        artist_source = 'yt' if artist_url[0] == 'U' else 'sp'
    else:
        artist_uri = results[0]
        artist_source = results[1]
    return {'name': artist_name, 'uri': artist_uri, 'source': artist_source}


THUMBNAIL_SIZES = ['maxres', 'standard', 'high', 'medium', 'default']

# save album_urls for checking later
cursor.execute('SELECT id, source, uri FROM albums')
album_data = cursor.fetchall()
album_ids = [row[0] for row in album_data]
album_uri_matches = [row[1] + row[2] for row in album_data]

cursor.execute('select id, source, uri from artists where not uri is null')
artist_data = cursor.fetchall()
artist_ids = [row[0] for row in artist_data]
artist_uri_matches = [row[1] + row[2] for row in artist_data]

# save last_fm_str_tracks for checking later
cursor.execute('SELECT * FROM last_FM_str_tracks;')
last_fm_str_dict = {row[0]: row[1] for row in cursor.fetchall()}

# get max utc in db to determine where to start pulling recents from lastfm
cursor.execute('SELECT MAX(utc) FROM scrobbles')
db_max_time = cursor.fetchone()[0]
start_time = db_max_time + 1 if db_max_time else int(datetime(2024, 1, 2).timestamp())  # if db empty, start on 1/2/2024
last_added_utc = start_time


def process_track(utc, lfm_artist, lfm_album, lfm_title, db, cursor, sp):
    print(f'Searching for {lfm_title} by {lfm_artist} off of {lfm_album}.')

    bridge_codes = [strip_str(lfm_title + lfm_artist + lfm_album)]
    remove_comma_from_artist = lfm_artist
    while ', ' in remove_comma_from_artist:
        remove_comma_from_artist = remove_comma_from_artist[0:remove_comma_from_artist.rindex(', ')]
        bridge_codes.append(strip_str(lfm_title + remove_comma_from_artist + lfm_album))

    if bridge_codes[0] in last_fm_str_dict:
        track_id = last_fm_str_dict[bridge_codes[0]]
    else:
        sp_tracks = sp.search(q=f'track:{remove_apostrophe_and_percent(lfm_title)} artist:{remove_apostrophe_and_percent(remove_comma_from_artist)}', type='track', limit=10)['tracks']['items']

        good_track = search_spotify_tracks(sp_tracks, bridge_codes)
        # uncomment this if you Quit out of adding a track because it is bad
        # good_track = False

        if not good_track:
            print(f'Any ideas? Track is {lfm_title} by {lfm_artist} off {lfm_album}. {"\nHere are some possible tracks" if sp_tracks else ""}')
            for sp_track in sp_tracks:
                print(f"{sp_track['name']} by {sp_track['artists'][0]['name']} off {sp_track['album']['name']}. url is {sp_track['external_urls']['spotify']}")
            url = input('\nIf you can find the song, enter the url. If not, press enter. ')
            if not url:
                return
            elif url[0:30] == 'https://open.spotify.com/track':
                good_track = sp.track(url)
            elif url[0:32] == 'https://www.youtube.com/watch?v=' or url[0:17] == 'https://youtu.be/':
                track_source = 'yt'
                album_source = 'yt'
                uri = url[(32 if url[8] == 'w' else 17):]
                if 'list' in uri:
                    uri = uri[:uri.index('list') - 1]
                if '&pp' in uri:
                    uri = uri[:uri.index('&pp')]
                data = requests.get(f'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id='
                                    f'{uri[:uri.index('?')] if '?' in uri else uri}&key={YOUTUBE_API_KEY}').json()['items'][0]
                runtime = input('runtime? ') if '&' in uri else iso_to_seconds(data['contentDetails']['duration'])
                snippet = data['snippet']
                image = None

                # siIvaGunner song
                if snippet['channelId'] == 'UC9ecwl3FTG66jIKA9JRDtmg':
                    dash_location = snippet['title'].rfind('-')
                    title = snippet['title'][:dash_location - 1]
                    album_title = snippet['title'][dash_location + 2:]
                    album_type = 'album'
                    artists = [{'name': 'SiIvaGunner', 'uri': 'UC9ecwl3FTG66jIKA9JRDtmg', 'source': 'yt'}]
                    playlist_index = snippet['description'].find('?list=')+6
                    if playlist_index != -1:
                        album_uri = snippet['description'][playlist_index:min((snippet['description']+'\n').find('\n', playlist_index), (snippet['description']+'\r').find('\r', playlist_index))]
                    else:
                        album_uri = input("Input playlist url: ")[38:]
                    yt_api_type = 'playlists'
                # from Pokemon DP OST Youtube video
                elif data['id'] == 'XDg0T0hsJkc':
                    title = lfm_title
                    description = snippet['description']
                    title_index = description.rfind(title)
                    while title_index == -1:
                        title = input('Title not found in description pls fix: ')
                        title_index = description.rfind(title)
                    this_line_start = description.rfind('\n', 0, title_index)
                    this_timestamp = description[this_line_start + 1:description.find(' ', this_line_start)].split(':')
                    this_seconds = int(this_timestamp[0]) * 3600 + int(this_timestamp[1]) * 60 + int(this_timestamp[2])
                    next_line_start = description.find('\n', title_index)
                    next_timestamp = description[next_line_start + 1:description.find(' ', next_line_start)].split(':')
                    next_seconds = int(next_timestamp[0]) * 3600 + int(next_timestamp[1]) * 60 + int(next_timestamp[2])

                    uri = f'{uri}?t={this_seconds}'
                    runtime = next_seconds - this_seconds

                    album_title = 'Pokémon Diamond and Pearl OST'
                    artist_name = lfm_artist.split(';')[0]
                    artists = [{'name': artist_name, 'uri': POKEMON_ARTIST_URIS[artist_name], 'source': 'sp'}]
                    album_uri = 'XDg0T0hsJkc'
                    yt_api_type = 'videos'
                else:
                    corrected_title = input(f"If {lfm_title} is the wrong title, put it in correctly here: ")
                    title = corrected_title if corrected_title else lfm_title
                    album_type = input("Album type? ")
                    if album_type in ['single', 'video']:
                        album_title = title if album_type == 'single' else input("Album title? ")
                        album_uri = uri[:uri.index('?')] if '?' in uri else uri
                        yt_api_type = 'videos'
                    else:
                        album_url = input("Input playlist url: ")
                        if album_url[0:31] == 'https://open.spotify.com/album/':
                            sp_album = sp.album(album_url)
                            album_type = sp_album['album_type']
                            album_title = sp_album['name']
                            album_uri = sp_album['id']
                            album_source = 'sp'
                            image = sp_album['images'][0]['url'][24:]
                        elif album_url[:38] == 'https://www.youtube.com/playlist?list=':
                            album_title = input("Album title? ")
                            album_uri = album_url[38:]
                            yt_api_type = 'playlists'
                        else:
                            album_uri = album_url
                            album_source = 'other'
                            album_title = input("Album title? ")

                    artists = []
                    corrected_artist = input("If the primary artist's name is wrong, put it in correctly here: ") or lfm_artist
                    artists.append(get_artist_object(corrected_artist))
                    additional_artist_name = input("Other artists? Add name here: ")
                    while additional_artist_name:
                        artists.append(get_artist_object(additional_artist_name))
                        additional_artist_name = input("Other artists? Add name here: ")

                if album_source == 'yt':
                    youtube_api_result = requests.get(f'https://www.googleapis.com/youtube/v3/{yt_api_type}?part=snippet&id={album_uri}&key={YOUTUBE_API_KEY}').json()['items']
                    if youtube_api_result: 
                        thumbnails = youtube_api_result[0]['snippet']['thumbnails']
                        for size in THUMBNAIL_SIZES:
                            if size in thumbnails:
                                image = thumbnails[size]['url'][23:-11]
                                break

                if not image:
                    image = input("Input image url: ")
            else:
                raise Exception("Couldn't parse link, bruh, what'd you do???")

        if good_track:
            title = good_track['name']
            uri = good_track['id']
            track_source = 'sp'
            album_type = good_track['album']['album_type']
            album_title = good_track['album']['name']
            album_uri = good_track['album']['id']
            album_source = 'sp'
            image = good_track['album']['images'][0]['url'][24:]
            artists = [{'name': artist['name'], 'uri': artist['id'], 'source': 'sp'} for artist in good_track['artists']]
            runtime = int(good_track['duration_ms'] / 1000)

        # strip all uris to ensure whitespace doesn't sneak into db
        uri = uri.strip()
        album_uri = album_uri.strip()
        for artist in artists:
            artist['uri'] = artist['uri'].strip()

        cursor.execute('SELECT id FROM tracks WHERE uri = %s AND source = %s', [uri, track_source])
        results = cursor.fetchone()
        if results:
            track_id = results[0]
        else:
            input(f'Adding {title} by {artists[0]['name']} off {album_title}. Press Ctrl-C now if this is a mistake')
            album_uri_match = album_source + album_uri
            if album_uri_match in album_uri_matches:
                album_id = album_ids[album_uri_matches.index(album_uri_match)]
            else:
                cursor.execute('INSERT INTO albums (uri, name, type, source, image) VALUES (%s, %s, %s, %s, %s)', (album_uri, album_title, album_type, album_source, image))
                album_id = cursor.lastrowid
                album_uri_matches.append(album_uri_match)
                album_ids.append(album_id)
            cursor.execute('INSERT INTO tracks (name, album_id, uri, runtime, source) VALUES (%s, %s, %s, %s, %s)', (title, album_id, uri, runtime, track_source))
            track_id = cursor.lastrowid

            primary = 1
            for artist in artists:
                artist_uri = artist['uri']
                artist_source = artist['source']
                artist_uri_match = artist_source + artist_uri
                if artist_uri_match in artist_uri_matches:
                    artist_id = artist_ids[artist_uri_matches.index(artist_uri_match)]
                else:
                    cursor.execute('INSERT INTO artists (name, uri, source) VALUES (%s, %s, %s)', (artist['name'], artist_uri, artist_source))
                    artist_id = cursor.lastrowid
                    artist_uri_matches.append(artist_uri_match)
                    artist_ids.append(artist_id)
                cursor.execute('INSERT INTO tracks_artists (track_id, artist_id, main) VALUES (%s, %s, %s)', (track_id, artist_id, primary))
                primary = 0

        cursor.execute('INSERT INTO last_fm_str_tracks (last_fm_str, track_id) VALUES (%s, %s)', (bridge_codes[0], track_id))
        last_fm_str_dict[bridge_codes[0]] = track_id

    cursor.execute('INSERT INTO scrobbles (utc, track_id) VALUES (%s, %s)', (utc, track_id))

    db.commit()


for seconds in range(start_time, int(time.time()), 43200):
    result = requests.get(f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=benfry128&api_key={LAST_FM_API_KEY}&format=json&from={seconds}&to={seconds + 43200}&limit=200")
    tracks = result.json()['recenttracks']['track']

    if type(tracks) is dict:
        tracks = [tracks]

    date_str = datetime.fromtimestamp(seconds).strftime('%m/%d/%Y')
    print(f'Collecting lastfm data around {date_str} ...Got {len(tracks)} tracks')

    # remove first track if it's a now-playing track
    if tracks and '@attr' in tracks[0] and 'nowplaying' in tracks[0]['@attr'] and tracks[0]['@attr']['nowplaying']:
        del tracks[0]

    # sort tracks by utc to ensure that tracks aren't missed if the script errors out
    sorted_tracks = sorted(tracks, key=(lambda d: int(d['date']['uts'])))

    for track in sorted_tracks:
        utc = int(track['date']['uts'])
        if utc <= last_added_utc:
            utc = last_added_utc + 1

        lfm_artist = track['artist']['#text']
        lfm_album = track['album']['#text']
        lfm_title = track['name']

        process_track(utc, lfm_artist, lfm_album, lfm_title, db, cursor, sp)

        last_added_utc = utc
