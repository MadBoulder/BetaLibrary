import urllib.request
import urllib.parse
import json
import os
import os.path
import time
from datetime import date
import re
import math

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

ENCODING = 'utf-8'
MAX_ITEMS_API_QUERY = 50
Y_CRED = 'AIzaSyAbPC02W3k-MFU7TmvYCSXfUPfH10jNB7g'


def get_channel_info(channel_id='UCX9ok0rHnvnENLSK7jdnXxA'):
    """
    Get the info of a YouTube channel from the channel's id
    """
    api_key = None
    with open('credentials.txt', 'r', encoding='utf-8') as f:
        api_key = f.read()
    query_url = 'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={}&key={}'.format(
        channel_id, api_key)
    inp = urllib.request.urlopen(query_url)
    return json.load(inp)


def get_video_info(id, api_key):
    """
    Get the details of a YouTube video from its id
    """
    # api_key = None
    # with open('credentials.txt', 'r', encoding='utf-8') as f:
    #     api_key = f.read()
    query_url = 'https://www.googleapis.com/youtube/v3/videos?part=statistics&id={}&key={}'.format(
        id, api_key)
    inp = urllib.request.urlopen(query_url)
    return json.load(inp)


def update_video_stats(video_data):
    """
    Update the stats of the channel videos
    """
    total = len(video_data)
    current = 0
    for video in video_data:
        print(current * 100 / total)
        v_stats = get_video_info(video['id'], Y_CRED)
        video['stats'] = v_stats['items'][0]['statistics']
        current += 1
    return video_data


def get_videos_from_channel(channel_id='UCX9ok0rHnvnENLSK7jdnXxA', num_videos=MAX_ITEMS_API_QUERY, page_token=None):
    """
    Get the title, description and id of all the videos uploaded to a channel
    """
    api_key = None
    with open('credentials.txt', 'r', encoding='utf-8') as f:
        api_key = f.read()

    url = 'https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={}&key={}'.format(
        channel_id, api_key
    )
    inp = urllib.request.urlopen(url)
    resp = json.load(inp)
    upload_playlist = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    progress = 0
    videos = []
    total_video_count = int(
        get_channel_info()['items'][0]['statistics']['videoCount'])

    while progress < total_video_count:
        print(str(round((progress/total_video_count)*100, 2))+'%')

        get_videos_url = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults={}&playlistId={}&key={}'.format(
            MAX_ITEMS_API_QUERY, upload_playlist, api_key
        )
        if page_token:
            get_videos_url += '&pageToken=' + resp['nextPageToken']

        inp = urllib.request.urlopen(get_videos_url)
        resp = json.load(inp)
        for video in resp['items']:
            v_data = {}
            v_data['title'] = video['snippet']['title']
            v_data['date'] = video['snippet']['publishedAt']
            v_data['description'] = video['snippet']['description']
            v_data['id'] = video['snippet']['resourceId']['videoId']
            v_data['url'] = get_video_url_from_id(v_data['id'])
            v_stats = get_video_info(v_data['id'], api_key)
            v_data['stats'] = v_stats['items'][0]['statistics']
            videos.append(v_data)

        progress += 50

        if resp.get('nextPageToken', False):
            page_token = resp.get('nextPageToken')
        else:
            page_token = None

    return videos


def update_videos_from_channel(
    channel_id='UCX9ok0rHnvnENLSK7jdnXxA', 
    num_videos=MAX_ITEMS_API_QUERY, 
    page_token=None, 
    data=None
    ):
    """
    Update the list of videos uploaded to the channel. If there are new videos,
    add them to the database
    """
    # compare number of videos
    video_data = data['items']
    video_ids = [v['id'] for v in video_data]

    total_video_count = int(
        get_channel_info()['items'][0]['statistics']['videoCount'])
    if len(video_data) >= total_video_count:
        print('Already up to date, updating stats')
        video_data = update_video_stats(video_data)
        return video_data

    # there are new videos, get them
    api_key = None
    with open('credentials.txt', 'r', encoding='utf-8') as f:
        api_key = f.read()

    url = 'https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={}&key={}'.format(
        channel_id, api_key
    )
    inp = urllib.request.urlopen(url)
    resp = json.load(inp)
    upload_playlist = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    missing_videos = total_video_count - len(video_data)
    progress = 0
    current_iter = 0
    max_iters = math.ceil(total_video_count/MAX_ITEMS_API_QUERY)
    new_videos = []
    while progress < missing_videos and current_iter < max_iters:
        print(str(round((progress/missing_videos)*100, 2)) + '%')

        get_videos_url = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults={}&playlistId={}&key={}'.format(
            MAX_ITEMS_API_QUERY, upload_playlist, api_key
        )
        if page_token:
            get_videos_url += '&pageToken=' + resp['nextPageToken']

        inp = urllib.request.urlopen(get_videos_url)
        resp = json.load(inp)
        for video in resp['items']:
            if video['snippet']['resourceId']['videoId'] not in video_ids:
                v_data = {}
                v_data['title'] = video['snippet']['title']
                v_data['date'] = video['snippet']['publishedAt']
                v_data['description'] = video['snippet']['description']
                v_data['id'] = video['snippet']['resourceId']['videoId']
                v_data['url'] = get_video_url_from_id(v_data['id'])
                v_stats = get_video_info(v_data['id'], api_key)
                v_data['stats'] = v_stats['items'][0]['statistics']
                new_videos.append(v_data)

        progress = len(new_videos)
        current_iter += 1

        if resp.get('nextPageToken', False):
            page_token = resp.get('nextPageToken')
        else:
            page_token = None
    updated_data = update_video_stats(new_videos + video_data)
    return updated_data


def get_video_url_from_id(video_id):
    """
    Given the ID of a video, return its URL
    """
    return 'https://www.youtube.com/watch?v={}'.format(video_id)


def load_data(infile=None, data=None):
    """
    Load current video data stored in the project folder
    """
    video_data = []
    if infile:
        # load from file
        with open(infile, 'r', encoding='utf-8') as f:
            try:
                video_data = json.load(f)['items']
            except:
                pass
    if data:
        video_data = data
    return video_data


def match_regex_and_add_field(pattern, infield, outfield, video_data):
    """
    Given a regex pattern and a field, find the sequence that matches
    the regex in the specified video field. Add the matched sequence as
    the specified new video field
    """
    reg_pattern = re.compile(pattern)
    for video in video_data:
        matches = reg_pattern.findall(video[infield])
        if matches:
            video[outfield] = matches[0]
        else:
            video[outfield] = 'Unknown'
    return video_data


def process_grade_data(infile=None, data=None):
    """
    Extract grade information from video data
    """
    video_data = load_data(infile, data)
    # This regex only matches french grades.
    grade_regex = r', (\d{1}[A-Za-z]?\+?\-?\??(?:\/\d?\w?\+?)?)(?: \(sit\))?(?: \(trav\))?(?: \(stand\))?\.? '
    return match_regex_and_add_field(grade_regex, 'title', 'grade', video_data)


def process_climber_data(infile=None, data=None):
    """
    Extract climber name from video data
    """
    video_data = load_data(infile, data)
    # regex to match climbers.
    climber_regex = r'(?:Climber: ?)(@?\w+ ?(?:\w+)?)'
    return match_regex_and_add_field(climber_regex, 'description', 'climber', video_data)


def process_zone_data(infile=None, data=None):
    """
    Extract zone name from video data
    """
    video_data = load_data(infile, data)
    # regex to match zones.
    zone_regex = r'(?:\.+.+)?(?:\. )(.+)$'
    video_data = match_regex_and_add_field(
        zone_regex, 'title', 'zone', video_data)
    for video in video_data:
        if video['zone'][-1] == '.':
            video['zone'] = video['zone'][:-1]

    # make a second pass to see if there is any unknown zone
    # that we can fix
    unique_zones = set([v['zone'] for v in video_data])
    for video in video_data:
        if video['zone'] == 'Unknown':
            for zone in unique_zones:
                if zone in video['title']:
                    video['zone'] = zone

    return video_data


def get_and_update_data_local(
        outfile='data/channel/raw_video_data.json',
        infile='data/channel/raw_video_data.json',
        is_update=True
    ):
    """
    Load current data from local file, update it and store it back.
    """
    video_data = []
    with open(infile, 'r', encoding='utf-8') as f:
        try:
            video_data = json.load(f)
        except:
            pass

    if is_update:
        video_data = update_videos_from_channel(
            page_token=None, data=video_data)
    else:
        video_data = get_videos_from_channel(page_token=None)

    with open(outfile, 'w', encoding='utf-8') as f:
        print('Videos retrieved: ' + str(len(video_data)))
        json.dump({'date': str(date.today()),
                   'items': video_data}, f, indent=4)

    processed_data = process_grade_data(data=video_data)
    processed_data = process_climber_data(data=processed_data)
    processed_data = process_zone_data(data=processed_data)

    with open('data/channel/processed_data.json', 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                   'items': processed_data}, f, indent=4)

    return {'date': str(date.today()), 'items': processed_data}


def get_and_update_data_firebase(is_update=True):
    """
    Load current data from firebase database, update it and store it back.
    """
    print('Updating data')
    if not firebase_admin._apps:
        cred = credentials.Certificate('madboulder.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://madboulder.firebaseio.com'
        })

    root = db.reference()

    # retrieve current videos
    if is_update:
        videos = root.child('video_data').get()
        video_data = update_videos_from_channel(page_token=None, data=videos)
    else:
        video_data = get_videos_from_channel(page_token=None)

    processed_data = process_grade_data(data=video_data)
    processed_data = process_climber_data(data=processed_data)
    processed_data = process_zone_data(data=processed_data)

    video_data = {
        'date': str(date.today()),
        'items': processed_data
    }

    # Update videos
    root.child('video_data').set(video_data)

    return video_data


def get_data_firebase():
    """
    Get data from firebase
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate('madboulder.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://madboulder.firebaseio.com'
        })

    root = db.reference()
    return root.child('video_data').get()


def get_last_update_date():
    """
    Retrieve the date when the data was last updated
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate('madboulder.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://madboulder.firebaseio.com'
        })

    root = db.reference()
    return root.child('video_data/date').get()

def get_contributors_count():
    """
    Get the number of contributors
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate('madboulder.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://madboulder.firebaseio.com'
        })
    return db.reference().child('contributor_count').get()

def get_data_local():
    """
    Get data from local files
    """
    video_data = {}
    with open('data/channel/processed_data.json', 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    return video_data


def set_zone_data(zone_data):
    if not firebase_admin._apps:
        cred = credentials.Certificate('madboulder.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://madboulder.firebaseio.com'
        })

    root = db.reference()
    root.child('zone_data').set(zone_data)


def update_zone_data():
    zone_data = get_zone_data()
    # Update the number of videos of each zone,
    #  rest should remain equal
    for zone in zone_data:
        zone['videos'] = get_number_of_videos_from_playlist(zone['playlist'])
    set_zone_data(zone_data)


def get_zone_data():
    if not firebase_admin._apps:
        cred = credentials.Certificate('madboulder.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://madboulder.firebaseio.com'
        })

    root = db.reference()
    return root.child('zone_data').get()

def get_number_of_videos_from_playlist(playlist):
    """
    Given a playlist, return the number of videos it has
    """
    with open('credentials.txt', 'r', encoding=ENCODING) as f:
        api_key = f.read()

    query_url = f'https://www.googleapis.com/youtube/v3/playlists?part=contentDetails&id={playlist}&key={api_key}'
    inp = urllib.request.urlopen(query_url)
    resp = json.load(inp)
    return resp['items'][0]['contentDetails']['itemCount']

if __name__ == '__main__':
    # for local update
    # get_and_update_data_local()
    # for firebase
    updated_data = get_and_update_data_firebase(is_update=True)

    # local update
    with open('data/channel/processed_data.json', 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=4)
    # get_zone_data()
