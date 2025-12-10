import utils
import matplotlib.pyplot as plt

sp = utils.spotipy_setup()

(db, cursor) = utils.db_setup()

"""
This is supposed to plot popularity vs my personal play count for various tracks, but it doesn't really show very much
Also of note, popularity is not actually super accurate because it's related to the specific album it's on
And in order to minimize the number of albums in the db, sometimes my uris point to specific deluxe versions of albums which are less popular than the normal version, resulting in way lower popularity scores for those tracks
"""
cursor.execute('select count(*), popularity from scrobbles join tracks on track_id = id where utc > 1735711200 and popularity is not null group by track_id order by count(*) desc;')

xs_and_ys = cursor.fetchall()

plays = [x_and_y[0] for x_and_y in xs_and_ys]
popularity = [x_and_y[1] for x_and_y in xs_and_ys]

fig, ax = plt.subplots()

ax.scatter(popularity, plays)

ax.set_xlabel('Popularity')
ax.set_ylabel('Play Count')

plt.show()
