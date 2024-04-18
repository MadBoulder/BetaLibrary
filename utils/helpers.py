import urllib.request
import urllib.parse
import json
import html
import os
import os.path
import shutil
import utils.zone_helpers
import utils.MadBoulderDatabase
import utils.channel

NAME = 'name'

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
    playlists = utils.MadBoulderDatabase.getPlaylistsData()
    sectors = {}
    for areaCode, playlist in playlists.items():
        for sector in playlist.get('sectors', {}):
            sector_data = playlist['sectors'][sector]
            sector_data['zone_code'] = areaCode
            sector_data['zone_name'] = playlist['title']
            sectors[sector] = sector_data
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


def search_zone(query, max_score=0):
    zone_data = utils.MadBoulderDatabase.getAreasData()
    return search(query, zone_data, max_score)


def search_sector(query, max_score=0):
    sectors = load_sectors()
    return search(query, sectors, max_score)


def search_problem(query, max_score=0):
    data = utils.MadBoulderDatabase.get_video_data_search_optimized()
    return search(query, data, max_score)

    
def simple_search(query, items, max_score=0):
    results = []
    
    if not query:
        return []
    
    for item in items:
        name = item.get("name", "").lower()
        if query.lower() in name:
            results.append(item)

    return results
    

def search(query, items, max_score=0):
    """
    From an input search query, return all matches with a score of 0 or lower than max_score.

    The score is computed as:
        - 0 if perfect match
        - levenshtein / (longest substring ^ 4 + 1) otherwise
    """

    if not query:
        return []
    
    for item in items.values():
        lev, long_sub = measure_similarity(query, item[NAME])
        score = lev / (long_sub ** 4 + 1)
        item['score'] = score
        # If the inputed text is entirely matched in a item,
        # add a score of 0
        if long_sub == len(query):
            item['score'] = 0
    itemps_to_show = [item for item in items.values() if item['score'] <= max_score]
    # Sort by score
    itemps_to_show.sort(key=lambda x: x['score'])
    
    return itemps_to_show


def getLastVideosFromChannel(num_videos=6):
    response = utils.channel.fetchLastPublishedVideos(num_videos)
    video_links = [utils.channel.getEmbedUrl(item['id']['videoId']) for item in response['items']]
    return video_links


def searchVideosInChanel(videoName, results=5):
    response = utils.channel.searchForVideosByName(videoName, results)
    videos = [{
        'title': html.unescape(item['snippet']['title']),
        'video_url': utils.channel.getEmbedUrl(item['id']['videoId']),
        'url': utils.channel.getUrl(item['id']['videoId'])
    } for item in response['items']]

    return videos


def get_number_of_videos_for_zone(zone_name):
    print("get_number_of_videos_for_zone")
    """
    Given a zone name, return the number of betas of the zone
    """
    playlist_data = utils.MadBoulderDatabase.getPlaylistsData()

    for item in playlist_data:
        if item['zone_code'] == zone_name:
            return item['video_count']
            
    return 0


def format_views(number):
    if number >= 1_000_000:
        formatted_number = number / 1_000_000
        return f"{formatted_number:.2f}M".rstrip('0').rstrip('.') if formatted_number < 10 else f"{formatted_number:.1f}M".rstrip('0').rstrip('.') if formatted_number < 100 else f"{int(formatted_number)}M"
    elif number >= 1_000:
        formatted_number = number / 1_000
        return f"{formatted_number:.2f}k".rstrip('0').rstrip('.') if formatted_number < 10 else f"{formatted_number:.1f}k".rstrip('0').rstrip('.') if formatted_number < 100 else f"{int(formatted_number)}k"
    else:
        return str(number)


def get_all_areas_list():
    print("get_all_areas_list")
    video_data = utils.MadBoulderDatabase.getAllVideoData()

    all_areas = set()
    for video in video_data.values():
        zone_code = video['zone_code']
        all_areas.add(zone_code)

    return list(all_areas)


def find_item(items, key, value):
    for item in items:
        if item.get(key) == value:
            return item
    return None


def empty_and_create_dir(dir_path):
    if os.path.exists(dir_path):
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        os.mkdir(dir_path)


def generate_download_url(area, filename):
    """
    Given a specific are and the downloadable filename,
    generate a link that navigates to the file and enables
    its download.
    """
    return '/download/' + area + '/' + filename
