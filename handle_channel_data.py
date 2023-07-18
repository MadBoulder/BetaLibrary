from enum import Enum
import urllib.request
import urllib.parse
import json
from datetime import date
import re
import math

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

ENCODING = 'utf-8'
MAX_ITEMS_API_QUERY = 50
Y_CRED = 'AIzaSyAbPC02W3k-MFU7TmvYCSXfUPfH10jNB7g'

class Case(Enum):
    lower = 1
    upper = 2
    none = 3


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
    print("update_video_stats")
    total = len(video_data)
    current = 0
    for video in video_data:
        print(current * 100 / total)
        v_stats = get_video_info(video['id'], Y_CRED)
        video['stats'] = v_stats['items'][0]['statistics']
        current += 1
    return video_data


def retrieve_all_videos():
    total_video_count = int(get_channel_info()['items'][0]['statistics']['videoCount'])
    return retrieve_videos_from_channel(video_num=total_video_count)


def retrieve_missing_videos(
    data=None
):
    video_data = data['items']
    total_video_count = int(get_channel_info()['items'][0]['statistics']['videoCount'])
    missing_videos = total_video_count - len(video_data)
    video_ids = [v['id'] for v in video_data]
    return retrieve_videos_from_channel(video_num=missing_videos, video_ids=video_ids)


def retrieve_videos_from_channel(
    channel_id='UCX9ok0rHnvnENLSK7jdnXxA',
    page_token=None,
    video_ids=[],
    video_num=-1
):
    """
    Get the title, description and id of all the videos uploaded to a channel
    """
    print("retrieve_videos_from_channel")
    api_key = None
    with open('credentials.txt', 'r', encoding='utf-8') as f:
        api_key = f.read()

    url = 'https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={}&key={}'.format(
        channel_id, api_key
    )
    inp = urllib.request.urlopen(url)
    resp = json.load(inp)
    upload_playlist = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    max_iters = math.ceil(video_num/MAX_ITEMS_API_QUERY)
    current_iter = 0
    videos = []

    while len(videos) < video_num and current_iter < max_iters:
        print(str(round((len(videos)/video_num)*100, 2))+'%')

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
                videos.append(v_data)
            
        current_iter += 1

        if resp.get('nextPageToken', False):
            page_token = resp.get('nextPageToken')
        else:
            page_token = None

    return videos


def update_videos_from_channel(
    data=None
):
    """
    If there are new videos, add them to the database
    Update the list of videos uploaded to the channel. 
    """
    new_videos = []
    
    total_video_count = int(get_channel_info()['items'][0]['statistics']['videoCount'])
    video_data = data['items']
    missing_videos = total_video_count - len(video_data)
    if missing_videos > 0:
        new_videos = retrieve_missing_videos(data=data)
        
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


def match_regex_and_add_field(pattern, infield, outfield, video_data, case=Case.none):
    """
    Given a regex pattern and a field, find the sequence that matches
    the regex in the specified video field. Add the matched sequence as
    the specified new video field
    """
    reg_pattern = re.compile(pattern)
    for video in video_data:
        matches = reg_pattern.findall(video[infield])
        if not matches:
            video[outfield] = 'Unknown'
        elif case == Case.upper:
            video[outfield] = matches[0].upper()
        elif case == Case.lower:
            video[outfield] = matches[0].lower()
        else:
            video[outfield] = matches[0]
    return video_data


def process_name_data(infile=None, data=None):
    video_data = load_data(infile, data)
    name_regex = r'Name: \s*?(.*?)(?:\n|$)'
    return match_regex_and_add_field(name_regex, 'description', 'name', video_data)


def process_grade_data(infile=None, data=None):
    video_data = load_data(infile, data)
    grade_with_info_regex = r'Grade: \s*?(.*?)(?:\n|$)'
    video_data = match_regex_and_add_field(grade_with_info_regex, 'description', 'grade_with_info', video_data)
    grade_regex = r'Grade:\s*(.+?)(?:\s*\([^)]*\))?(?:\n|$)'
    return match_regex_and_add_field(grade_regex, 'description', 'grade', video_data, Case.upper)


def process_climber_data(infile=None, data=None):
    video_data = load_data(infile, data)
    climber_regex = r'Climber: \s*?(.*?)(?:\n|$)'
    return match_regex_and_add_field(climber_regex, 'description', 'climber', video_data)


def process_zone_data(infile=None, data=None):
    video_data = load_data(infile, data)
    zone_regex = r'Zone: \s*?(.*?)(?:\n|$)'
    return match_regex_and_add_field(zone_regex, 'description', 'zone', video_data)


def process_sector_data(infile=None, data=None):
    video_data = load_data(infile, data)
    sector_regex = r'Sector: \s*?(.*?)(?:\n|$)'
    return match_regex_and_add_field(sector_regex, 'description', 'sector', video_data)


def update_local_database(
    retrieve_data_from_channel=True
):
    if retrieve_data_from_channel:
        retrieve_and_update_data_raw_local(is_update=False)
    process_data_local()


def retrieve_and_update_data_raw_local(
    outfile='data/channel/raw_video_data.json',
    infile='data/channel/raw_video_data.json',
    is_update=True
):
    video_data = []
    if is_update:
        print("Updating raw_video_data.json file")
        raw_video_data_local = []
        with open(infile, 'r', encoding='utf-8') as f:
            try:
                raw_video_data_local = json.load(f)
            except:
                pass
        video_data = update_videos_from_channel(data=raw_video_data_local)
    else:
        print("Regenerating raw_video_data.json file")
        video_data = retrieve_all_videos()

    with open(outfile, 'w', encoding='utf-8') as f:
        print('Videos retrieved: ' + str(len(video_data)))
        json.dump({'date': str(date.today()),
                   'items': video_data}, f, indent=4)


def process_data_local(
    infile='data/channel/raw_video_data.json',
    outfile='data/channel/processed_data.json'
):
    print("Processing local data: Regenerating processed_data.json file");
    processed_data = process_name_data(infile=infile)
    processed_data = process_grade_data(data=processed_data)
    processed_data = process_climber_data(data=processed_data)
    processed_data = process_zone_data(data=processed_data)
    processed_data = process_sector_data(data=processed_data)

    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                   'items': processed_data}, f, indent=4)


def regenerate_firebase_data(is_update=True):
    """
    Load current data from local database and copy it to firebase database
    """
    print('Regenerating Firebase Data')
    if not firebase_admin._apps:
        cred = credentials.Certificate('madboulder.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://madboulder.firebaseio.com'
        })

    root = db.reference()

    # retrieve current videos
   #if is_update:
   #    videos = root.child('video_data').get()
   #    video_data = update_videos_from_channel(data=videos)
   #else:
   #    video_data = get_videos_from_channel(page_token=None)
   #
   #processed_data = process_grade_data(data=video_data)
   #processed_data = process_climber_data(data=processed_data)
   #processed_data = process_zone_data(data=processed_data)
   #
   #video_data = {
   #    'date': str(date.today()),
   #    'items': processed_data
   #}
    
    video_data = get_data_local()
    root.child('video_data').set(video_data)


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
    dry_run=False
    update_local_database()
        
    if not dry_run:
        regenerate_firebase_data()
