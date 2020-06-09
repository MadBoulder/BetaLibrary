import urllib.request, urllib.parse
import json
import os
import os.path

MAX_ITEMS_API_QUERY = 50

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


def load_zones():
    """
    Load the files and names of all the bouldering zones defined
    in ./data/zones.
    """
    areas = next(os.walk('data/zones/'))[1]
    zones = []
    for area in areas:
        datafile = 'data/zones/' + area + '/' + area + '.txt'
        area_data = {}
        with open(datafile, encoding='utf-8') as data:
            area_data = json.load(data)
        zones += [{'name': area_data['name'], 'file': area}]
    return zones

def load_sectors():
    """
    Load all sectors defined in the bouldering zones at ./data/zones.
    """
    areas = next(os.walk('data/zones/'))[1]
    sectors = []
    for area in areas:
        datafile = 'data/zones/' + area + '/' + area + '.txt'
        area_data = {}
        with open(datafile, encoding='utf-8') as data:
            area_data = json.load(data)
        for sector in area_data.get('sectors', []):
            sectors += [{'name': sector['name'], 'link': sector['link']}]
    return sectors

def count_sectors_in_zone(zone):
    """
    Given a zone name, return the number of sectors based on the
    zone's datafile specified sectors.
    """
    datafile = 'data/zones/' + zone + '/' + zone + '.txt'
    with open(datafile, encoding='utf-8') as data:
        area_data = json.load(data)
        return len(area_data['sectors'])


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
    if not query:
        return []
    zones = load_zones()
    for zone in zones:
        lev, long_sub = measure_similarity(query, zone['name'])
        score = lev / (long_sub ** 4 + 1)
        zone['score'] = score
        # If the inputed text is entirely matched in a zone,
        # add a score of 0
        if long_sub == len(query):
            zone['score'] = 0
    to_show = [zone for zone in zones if zone['score'] == 0]
    
    if exact_match:
        return to_show

    # Add zones required to reach min number of results if non exact
    # matches should be included
    if len(to_show) < num_results:
        # First remove already added zones
        zones = [zone for zone in zones if zone['score'] != 0]
        # Sort by score
        zones.sort(key=lambda x: x['score'])
        # Add the ones with the lowest score
        to_show += zones[0:num_results-len(to_show)]

    return to_show

def search_sector(query, num_results=4, exact_match=False):
    """
    From an input search query, return at least the 4 best
    matches from the sector list. A perfect match 
    (which is achieved when the input query is completely contained
    in the sector's name) is always returned. If the number of perfect
    matches is less than 4 then we add partial matches, via a score,
    until the list of results contains 4 entries.

    The score is computed as:
        - 0 if perfect match
        - levenshtein / (longest substring ^ 4 + 1) otherwise
    """
    if not query:
        return []
    sectors = load_sectors()
    for sector in sectors:
        lev, long_sub = measure_similarity(query, sector['name'])
        score = lev / (long_sub ** 4 + 1)
        sector['score'] = score
        # If the inputed text is entirely matched in a zone,
        # add a score of 0
        if long_sub == len(query):
            sector['score'] = 0
    to_show = [sector for sector in sectors if sector['score'] == 0]

    if exact_match:
        return to_show

    # Add zones required to reach min number of results if non exact
    # matches should be included
    if len(to_show) < num_results:
        # First remove already added zones
        sectors = [sector for sector in sectors if sector['score'] != 0]
        # Sort by score
        sectors.sort(key=lambda x: x['score'])
        # Add the ones with the lowest score
        to_show += sectors[0:num_results-len(to_show)]

    return to_show

def get_videos_from_channel(channel_id="UCX9ok0rHnvnENLSK7jdnXxA", num_videos=6):
    """
    Obtain the num_videos latest videos from MadBoulder's youtube channel
    """
    api_key = None
    with open("credentials.txt", "r", encoding='utf-8') as f:
        api_key = f.read()

    base_video_url = '//www.youtube.com/embed/'
    base_search_url = 'https://www.googleapis.com/youtube/v3/search?'

    url = base_search_url + \
        'key={}&channelId={}&part=snippet,id&order=date&maxResults={}&type=video'.format(
            api_key, channel_id, str(num_videos))

    video_links = []
    inp = urllib.request.urlopen(url)
    resp = json.load(inp)
    for i in resp['items']:
        if i['id']['kind'] == "youtube#video":
            video_links.append(base_video_url + i['id']['videoId'])
    return video_links


def get_channel_info(channel_id="UCX9ok0rHnvnENLSK7jdnXxA"):
    """
    Get the info of a youtube channel from the channel's id
    """
    api_key = None
    with open("credentials.txt", "r", encoding='utf-8') as f:
        api_key = f.read()
    query_url = 'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={}&key={}'.format(
        channel_id, api_key)
    inp = urllib.request.urlopen(query_url)
    return json.load(inp)


def get_video_from_channel(video_name, channel_id="UCX9ok0rHnvnENLSK7jdnXxA"):
    """
    API query format:
    https://www.googleapis.com/youtube/v3/search?q=%TEXT%27&part=snippet&type=video&channelId=CHANNEL_ID&key=API_KEY
    """
    api_key = None
    with open("credentials.txt", "r", encoding='utf-8') as f:
        api_key = f.read()
    base_video_url = '//www.youtube.com/embed/' # to embed video
    query_url = "https://www.googleapis.com/youtube/v3/search?q=%27{}%27&part=snippet&type=video&channelId={}&key={}".format(
        urllib.parse.quote(video_name), channel_id, api_key)
    inp = urllib.request.urlopen(query_url)
    resp = json.load(inp)
    for i in resp['items']:
        if i['id']['kind'] == "youtube#video":
            i['video_url'] = base_video_url + i['id']['videoId']
            i['url'] = 'https://www.youtube.com/watch?v=' + i['id']['videoId']
    return resp['items']


def get_number_of_videos_from_playlists_file(file):
    """
    Given a file with the playlist from which we want to obtain the
    number of videos, return a dict that maps a bouldering zone to
    the current number of videos via a query to Youtube's v3 data API

    The file should be structured like a Python dict in the following way:
    {
        'area_name':'playlist_link'
    }

    This function returns a dict that is structured like:
    {
        'area_name':video_count
    } 
    """
    api_key = None
    with open("credentials.txt", "r", encoding='utf-8') as f:
        api_key = f.read()

    data = {}
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    playlists = list(data.values())
    # We want to be able to get the playlist from the zone name
    # but also the zone name from the playlist
    data = bidict(data)
    total_resp = []
    for i in range(len(playlists)//MAX_ITEMS_API_QUERY + 1):
        query_url = 'https://www.googleapis.com/youtube/v3/playlists?part=contentDetails&id={}&key={}'.format(
            ','.join(playlists[i*MAX_ITEMS_API_QUERY:(i+1)*MAX_ITEMS_API_QUERY]), api_key)
        inp = urllib.request.urlopen(query_url)
        resp = json.load(inp)
        total_resp += resp['items']
    count = {}
    # Associate in a dict zone name with number of videos via
    # the playlist id. This dict will be the return value of the
    # function
    for i in total_resp:
        zone = data.inverse[i['id']][0]
        count[zone] = i['contentDetails']['itemCount']
    return count


def get_number_of_videos_for_zone(zone_name):
    """
    Given a zone name, return the number of betas of the zone
    """
    api_key = None
    with open("credentials.txt", "r", encoding='utf-8') as f:
        api_key = f.read()

    data = {}
    with open('./data/playlist.txt', 'r', encoding='utf-8') as f:
        data = json.load(f)
    query_url = 'https://www.googleapis.com/youtube/v3/playlists?part=contentDetails&id={}&key={}'.format(
        data[zone_name],
        api_key
    )
    inp = urllib.request.urlopen(query_url)
    resp = json.load(inp)
    return resp['items'][0]['contentDetails']['itemCount']
