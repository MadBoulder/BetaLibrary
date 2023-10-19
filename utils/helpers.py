import urllib.request
import urllib.parse
import json
import html
import os
import os.path
import utils.zone_helpers
from googleapiclient.discovery import build
from werkzeug.utils import secure_filename
import handle_channel_data


MAX_ITEMS_API_QUERY = 50
DATA_ZONES_PATH = 'data/zones/'
NAME = 'name'
ENCODING = 'utf-8'
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']

class bidict(dict):
    """
    Bidirectional dictionary. Given a normal Python dict it enables to retrieve values by
    key and keys by value
    """
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key], []).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)


def load_sectors():
    playlist_data = handle_channel_data.get_playlist_data()
    sectors = []
    for item in playlist_data['items']:
        for sector in item.get('sectors', []):
            sector['zone_code'] = item['zone_code']
            sector['zone_name'] = item['title']
            sectors.append(sector)
    return sectors


def count_sectors_in_zone(zone):
    """
    Given a zone name, return the number of sectors based on the
    zone's datafile specified sectors.
    """
    playlists = utils.zone_helpers.get_playlists_from_zone(zone)
    if playlists:
        return len(playlists.get('sectors', []))
    else:
        return 0


def iterative_levenshtein(s, t, costs=(1, 1, 3)):
    """ 
    iterative_levenshtein(s, t) -> ldist
    ldist is the Levenshtein distance between the strings 
    s and t.
    For all i and j, dist[i,j] will contain the Levenshtein 
    distance between the first i characters of s and the 
    first j characters of t

    costs: a tuple or a list with three integers (d, i, s)
           where d defines the costs for a deletion
                 i defines the costs for an insertion and
                 s defines the costs for a substitution

    Source: https://www.python-course.eu/levenshtein_distance.php
    """
    rows = len(s)+1
    cols = len(t)+1
    deletes, inserts, substitutes = costs

    dist = [[0 for x in range(cols)] for x in range(rows)]
    # source prefixes can be transformed into empty strings
    # by deletions:
    for row in range(1, rows):
        dist[row][0] = row * deletes
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for col in range(1, cols):
        dist[0][col] = col * inserts

    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = substitutes
            dist[row][col] = min(dist[row-1][col] + deletes,
                                 dist[row][col-1] + inserts,
                                 dist[row-1][col-1] + cost)  # substitution
    #  for r in range(rows):
    #      print(dist[r])
    return dist[row][col]


def lcw(u, v):
    """
    Return length of an LCW of strings u and v and its starting indexes.

    (l, i, j) is returned where l is the length of an LCW of the strings u, v
    where the LCW starts at index i in u and index j in v.

    Source: https://www.sanfoundry.com/python-program-find-longest-common-substring-using-dynamic-programming-bottom-up-approach/
    """
    # c[i][j] will contain the length of the LCW at the start of u[i:] and
    # v[j:].
    c = [[-1]*(len(v) + 1) for _ in range(len(u) + 1)]

    for i in range(len(u) + 1):
        c[i][len(v)] = 0
    for j in range(len(v)):
        c[len(u)][j] = 0

    lcw_i = lcw_j = -1
    length_lcw = 0
    for i in range(len(u) - 1, -1, -1):
        for j in range(len(v)):
            if u[i] != v[j]:
                c[i][j] = 0
            else:
                c[i][j] = 1 + c[i + 1][j + 1]
                if length_lcw < c[i][j]:
                    length_lcw = c[i][j]
                    lcw_i = i
                    lcw_j = j

    return length_lcw, lcw_i, lcw_j


def measure_similarity(query, zone):
    """
    Measure both levenshtein distance and lowest common string between
    the search query and the name of bouldering zone and return both values.
    This can be later used to determine search matches.
    """
    levenshtein = iterative_levenshtein(query, zone)
    longest_sub, _, _ = lcw(query.lower(), zone.lower())
    return levenshtein, longest_sub


def search_zone(query, num_results=4, exact_match=False):
    zone_data = handle_channel_data.get_zone_data()
    return search(query, zone_data['items'], num_results, exact_match)


def search_sector(query, num_results=4, exact_match=False):
    sectors = load_sectors()
    return search(query, sectors, num_results, exact_match)


def search_problem(query, num_results=4, exact_match=False):
    data = handle_channel_data.get_video_data_search_optimized()
    return search(query, data['items'], num_results, exact_match)

    
def simple_search(query, items, num_results=4, exact_match=False):
    """
    From an input search query, return at least the 4 best
    matches from the bouldering zones. A perfect match 
    (which is achieved when the input query is completely contained
    in the zone's name) is always returned. If the number of perfect
    matches is less than 4 then we add partial matches, via a score,
    until the list of results contains 4 entries.

    The score is computed as:
        - 0 if perfect match
        - levenshtein / (longest substring ^ 4 + 1) otherwise
    """
    results = []
    
    if not query:
        return []
    
    for item in items:
        name = item.get("name", "").lower()
        if query.lower() in name:
            results.append(item)

    return results
    
def search(query, items, num_results=4, exact_match=False):
   
    if not query:
        return []
    
    for item in items:
        lev, long_sub = measure_similarity(query, item[NAME])
        score = lev / (long_sub ** 4 + 1)
        item['score'] = score
        # If the inputed text is entirely matched in a item,
        # add a score of 0
        if long_sub == len(query):
            item['score'] = 0
    itemps_to_show = [item for item in items if item['score'] == 0]
    
    if exact_match:
        return itemps_to_show

    # Add items required to reach min number of results if non exact
    # matches should be included
    if len(itemps_to_show) < num_results:
        # First remove already added items
        no_match_items = [item for item in items if item['score'] != 0]
        # Sort by score
        no_match_items.sort(key=lambda x: x['score'])
        # Add the ones with the lowest score
        itemps_to_show += no_match_items[0:num_results-len(itemps_to_show)]

    return itemps_to_show

def get_videos_from_channel(channel_id='UCX9ok0rHnvnENLSK7jdnXxA', num_videos=6):
    """
    Obtain the num_videos latest videos from MadBoulder's youtube channel
    """
    base_video_url = '//www.youtube.com/embed/'
    base_search_url = 'https://www.googleapis.com/youtube/v3/search?'

    url = base_search_url + \
        'key={}&channelId={}&part=snippet,id&order=date&maxResults={}&type=video'.format(
            YOUTUBE_API_KEY, channel_id, str(num_videos))

    video_links = []
    inp = urllib.request.urlopen(url)
    resp = json.load(inp)
    for i in resp['items']:
        i['snippet']['title'] = html.unescape(i['snippet']['title'])
        if i['id']['kind'] == 'youtube#video':
            video_links.append(base_video_url + i['id']['videoId'])
    return video_links


def get_channel_info(channel_id='UCX9ok0rHnvnENLSK7jdnXxA'):
    """
    Get the info of a youtube channel from the channel's id
    """
    query_url = 'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={}&key={}'.format(
        channel_id, YOUTUBE_API_KEY)
    inp = urllib.request.urlopen(query_url)
    return json.load(inp)


def get_video_from_channel(video_name, channel_id='UCX9ok0rHnvnENLSK7jdnXxA', results=5):
    """
    API query format:
    https://www.googleapis.com/youtube/v3/search?q=%TEXT%27&part=snippet&type=video&channelId=CHANNEL_ID&key=API_KEY
    """
    try:
        base_video_url = '//www.youtube.com/embed/'  # to embed video
        query_url = "https://www.googleapis.com/youtube/v3/search?q=%27{}%27&part=snippet&type=video&channelId={}&key={}".format(
            urllib.parse.quote(video_name), channel_id, YOUTUBE_API_KEY)
        inp = urllib.request.urlopen(query_url)
        resp = json.load(inp)
        for i in resp['items']:
            if i['id']['kind'] == 'youtube#video':
                i['snippet']['title'] = html.unescape(i['snippet']['title'])
                i['video_url'] = base_video_url + i['id']['videoId']
                i['url'] = 'https://www.youtube.com/watch?v=' + i['id']['videoId']
        return resp['items'][0:results]
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def get_number_of_videos_for_zone(zone_name):
    print("get_number_of_videos_for_zone")
    """
    Given a zone name, return the number of betas of the zone
    """
    playlist_data = handle_channel_data.get_playlist_data()

    for item in playlist_data['items']:
        if item['zone_code'] == zone_name:
            return item['video_count']
            
    return 0


def generate_download_url(area, filename):
    """
    Given a specific are and the downloadable filename,
    generate a link that navigates to the file and enables
    its download.
    """
    return '/download/' + area + '/' + filename
