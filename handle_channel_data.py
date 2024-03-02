from enum import Enum
import urllib.request
import urllib.parse
import json
import threading
import subprocess
from datetime import date
import re
import math
import os
import time
from tempfile import mkstemp
from os import fdopen, remove
from shutil import move, copymode
from slugify import slugify

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from googleapiclient.discovery import build

ENCODING = 'utf-8'
MAX_ITEMS_API_QUERY = 50
CONFIG_FILE = 'config.py'
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY_HANDLE_DATA']

firebase_lock = threading.Lock()

class Case(Enum):
    lower = 1
    upper = 2
    none = 3


def get_channel_info(channel_id='UCX9ok0rHnvnENLSK7jdnXxA'):
    """
    Get the info of a YouTube channel from the channel's id
    """
    query_url = 'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={}&key={}'.format(
        channel_id, YOUTUBE_API_KEY)
    inp = urllib.request.urlopen(query_url)
    return json.load(inp)


def get_video_info(id):
    """
    Get the details of a YouTube video from its id
    """
    query_url = 'https://www.googleapis.com/youtube/v3/videos?part=statistics&id={}&key={}'.format(
        id, YOUTUBE_API_KEY)
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
        v_stats = get_video_info(video['id'])
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
    url = 'https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={}&key={}'.format(
        channel_id, YOUTUBE_API_KEY
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
            MAX_ITEMS_API_QUERY, upload_playlist, YOUTUBE_API_KEY
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
                v_stats = get_video_info(v_data['id'])
                v_data['stats'] = v_stats['items'][0]['statistics']
                videos.append(v_data)
            
        current_iter += 1

        if resp.get('nextPageToken', False):
            page_token = resp.get('nextPageToken')
        else:
            page_token = None

    return videos


def retrieve_playlists_from_channel(channel_id='UCX9ok0rHnvnENLSK7jdnXxA'):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    playlists = []
    next_page_token = None

    while True:
        response = youtube.playlists().list(
            part="snippet, contentDetails",
            channelId=channel_id,
            maxResults=50,  # You can change this number as per your requirement
            pageToken=next_page_token
        ).execute()

        playlists.extend(response["items"])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
      
    return playlists


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
    return  match_regex_and_add_field(zone_regex, 'description', 'zone', video_data)


def process_sector_data(infile=None, data=None):
    video_data = load_data(infile, data)
    sector_regex = r'Sector: \s*?(.*?)(?:\n|$)'
    return match_regex_and_add_field(sector_regex, 'description', 'sector', video_data)

def process_all_data(infile=None, data=None):
    video_data = load_data(infile, data)
    for video in video_data:
        video['name'] = get_problem_name(video)
        video['secure'] = slugify(video['name']) + '-'+ slugify(video['grade_with_info'])
        video['zone_code'] = slugify(video['zone'])
        video['sector_code'] = slugify(video['sector'])
        video['climber_code'] = slugify(video['climber'])

    return video_data


def get_problem_name(problem_data):
    """
    Ugly function to remove pieces from the video 
    title until we are left with the problem name
    """
    # remove grade from title?
    name = problem_data['name']
    if name == 'Unknown':
        name = problem_data['title'].replace(
            problem_data.get('zone', ''), ''
        ).replace(
            problem_data.get('grade', '').lower(), ''
        ).replace(
            problem_data.get('grade', '').upper(), ''
        ).replace(
            '(sit)',
            ''
        ).replace(
            '(stand)',
            ''
        ).replace(
            '(crouching start)',
            ''
        ).strip()

        if name[-1] == '.':
            name = name[:-1].strip()
        if name[-1] == ',':
            name = name[:-1].strip()
    return name


def update_local_database(
    retrieve_data_from_channel=True
):
    if retrieve_data_from_channel:
        retrieve_and_update_video_data_raw_local(is_update=False)
        retrieve_and_update_playlist_data_raw_local()
    process_video_data_local()
    process_playlist_data_local()
    process_zone_data_local()
    update_countries_list()


def retrieve_and_update_video_data_raw_local(
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
                   
                   
def retrieve_and_update_playlist_data_raw_local(
    outfile='data/channel/raw_playlist_data.json'
):
    print("Regenerating raw_playlist_data.json file")
    playlists = retrieve_playlists_from_channel()
                   
    with open(outfile, 'w', encoding='utf-8') as f:
        print('Playlists retrieved: ' + str(len(playlists)))
        json.dump({'date': str(date.today()),
                   'items': playlists}, f, indent=4)


def process_video_data_local(
    infile='data/channel/raw_video_data.json',
    outfile='data/channel/processed_data.json'
):
    print("Processing local data: Regenerating processed_data.json file")
    processed_data = process_name_data(infile=infile)
    processed_data = process_grade_data(data=processed_data)
    processed_data = process_climber_data(data=processed_data)
    processed_data = process_zone_data(data=processed_data)
    processed_data = process_sector_data(data=processed_data)
    processed_data = process_all_data(data=processed_data)
    
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                   'items': processed_data}, f, indent=4)
                   
    processed_data_search_optimized = processed_data
    processed_data_search_optimized = [video for video in processed_data_search_optimized if video['name'] != 'Unknown']
    for video in processed_data_search_optimized:
        del video['stats']
        del video['description']
        del video['id']
        del video['secure']
        del video['zone_code']
        del video['climber_code']
        del video['sector_code']
    
    with open('data/channel/processed_data_search_optimized.json', 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                   'items': processed_data_search_optimized}, f, indent=4)

         
def process_playlist_data_local(
    infile='data/channel/raw_playlist_data.json',
    outfile='data/channel/processed_playlist_data.json'
):
    print("Processing local data: Regenerating processed_zone_data.json file")
    
    raw_playlist_data = []
    with open(infile, 'r', encoding='utf-8') as f:
        try:
            raw_playlist_data = json.load(f)
        except:
            pass
    
    processed_playlist_data = []
    print("Processing local data: processing raw playlist data")
    for i in raw_playlist_data['items']:
        title = i['snippet']['title']
        is_sector = 'Sector' in title
        zone_name, sector_name = title.split(': Sector ') if is_sector else (title, None)
            
        playlist_json_object = []
        for p in processed_playlist_data:
            if p['title'] == zone_name:
                playlist_json_object = p
                break
        
        if not playlist_json_object:
            playlist_json_object = {"title": zone_name, "sectors": []}
            processed_playlist_data.append(playlist_json_object)
            
        if not is_sector:
            playlist_json_object['zone_code'] = slugify(zone_name)
            playlist_json_object['id'] = i['id']
            playlist_json_object['video_count'] = i['contentDetails']['itemCount']
            playlist_json_object['thumbnail'] = get_playlist_thumbnail(i['snippet']['thumbnails'])
        else:
            playlist_json_object['sectors'].append({"name": sector_name, 
                                                    "sector_code": slugify(sector_name), 
                                                    "id": i['id'],
                                                    "video_count": i['contentDetails']['itemCount']})
    
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                   'items': processed_playlist_data}, f, indent=4)
                   
         
def process_zone_data_local(
    outfile='data/channel/zone_data.json'
):
    print("Processing local data: Generating zone_data.json file")
    
    if os.path.exists('data/zones'):
        zones = next(os.walk('data/zones/'))[1]
        zones_data = []
        for zone_code in zones:
            datafile = 'data/zones/' + zone_code + '/' + zone_code + '.json'
            print(datafile)
            with open(datafile, encoding='utf-8') as data:
                zone_data = json.load(data)
                zone_data['zone_code'] = slugify(zone_data['name'])
                zone_data['altitude'] = get_altitude_from_coordinates(zone_data['latitude'], zone_data['longitude'])
                zones_data.append(zone_data)
        
        with open(outfile, 'w', encoding='utf-8') as f:
            json.dump({'date': str(date.today()),
                       'items': zones_data}, f, indent=4)
   
   
def get_playlist_thumbnail(thumbnails):
    thumbnailUrl = None

    if 'maxres' in thumbnails:
        thumbnailUrl = thumbnails['maxres']['url']
    elif 'standard' in thumbnails:
        thumbnailUrl = thumbnails['standard']['url']
    elif 'high' in thumbnails:
        thumbnailUrl = thumbnails['high']['url']
    elif 'medium' in thumbnails:
        thumbnailUrl = thumbnails['medium']['url']
    elif 'default' in thumbnails:
        thumbnailUrl = thumbnails['default']['url']
    
    return thumbnailUrl
    
    
def get_altitude_from_coordinates(latitude, longitude):
    url = f"https://api.opentopodata.org/v1/aster30m?locations={latitude},{longitude}"
    try:
        result = subprocess.run(["curl", url], stdout=subprocess.PIPE, text=True, check=True)
        time.sleep(0.7)#in order to not overflow the free API
        data = json.loads(result.stdout)
        if "results" in data and len(data["results"]) > 0:
            elevation = data["results"][0]["elevation"]
            print(elevation)
            return elevation
        else:
            print("No elevation data found in the response.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error while running curl: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

   

def get_zone_code_from_name(zone_name, path = 'data/zones'):
    file_list = os.listdir(path)
    for filename in file_list:
        full_path = os.path.join(path, filename)

        if os.path.isfile(full_path) and filename.endswith('.json'):
            with open(full_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
            if 'name' in json_data and zone_name == json_data['name']:
                return os.path.splitext(filename)[0]

        elif os.path.isdir(full_path) and not filename == 'sectors':
            result = get_zone_code_from_name(zone_name, full_path)
            if result:
                return result

    return None


def regenerate_firebase_data(is_update=True):
    """
    Load current data from local database and copy it to firebase database
    """
    print('Regenerating Firebase Data')
    
    with firebase_lock:
        if not firebase_admin._apps:
            cred = credentials.Certificate('madboulder.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://madboulder.firebaseio.com'
            })

    root = db.reference()
    
    video_data = get_video_data_local()
    root.child('video_data').set(video_data)
    
    video_data_search_optimized = get_video_data_local_search_optimized()
    root.child('video_data_search_optimized').set(video_data_search_optimized)
    
    playlist_data = get_playlist_data_local()
    root.child('playlist_data').set(playlist_data)
    
    zone_data = get_zone_data_local()
    root.child('zone_data').set(zone_data)
    
    country_data = get_country_data_local()
    root.child('country_data').set(country_data)
    
    num_climbers = len(list({slugify(video['climber']) for video in video_data['items']}))
    root.child('contributor_count').set(num_climbers)
    
    num_videos = len(video_data['items'])
    root.child('video_count').set(num_videos)


def get_video_data():
    return get_element_from_firebase('video_data')
    
def get_video_data_search_optimized():
    return get_element_from_firebase('video_data_search_optimized')

def get_contributors_count():
    return get_element_from_firebase('contributor_count')

def get_video_count():
    return get_element_from_firebase('video_count')

def get_playlist_data():
    return get_element_from_firebase('playlist_data')

def get_zone_data():
    return get_element_from_firebase('zone_data')

def get_country_data():
    return get_element_from_firebase('country_data')
    
def get_element_from_firebase(element_name):
    with firebase_lock:
        if not firebase_admin._apps:
            cred = credentials.Certificate('madboulder.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://madboulder.firebaseio.com'
            })

    root = db.reference()
    return root.child(element_name).get()


def get_last_update_date():
    """
    Retrieve the date when the data was last updated
    """
    with firebase_lock:
        if not firebase_admin._apps:
            cred = credentials.Certificate('madboulder.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://madboulder.firebaseio.com'
            })

    root = db.reference()
    return root.child('video_data/date').get()
    

def get_video_data_local_search_optimized():
    video_data = {}
    with open('data/channel/processed_data_search_optimized.json', 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    return video_data
    
def get_video_data_local():
    video_data = {}
    with open('data/channel/processed_data.json', 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    return video_data
    

def get_playlist_data_local():
    zone_data = {}
    with open('data/channel/processed_playlist_data.json', 'r', encoding='utf-8') as f:
        zone_data = json.load(f)
    return zone_data
    

def get_zone_data_local():
    zone_data = {}
    with open('data/channel/zone_data.json', 'r', encoding='utf-8') as f:
        zone_data = json.load(f)
    return zone_data
    

def get_country_data_local():
    zone_data = {}
    with open('data/countries.json', 'r', encoding='utf-8') as f:
        zone_data = json.load(f)
    return zone_data



def update_countries_list(input_file=CONFIG_FILE):
    """
    Update the current list of countries where 
    we have bouldering zones
    """
    # TODO: If a location has no country set, 
    # this function should fallback and compute it
    # Update contries list
    zone_data = get_zone_data_local()
    countries_list = [f'\'{c}\'' for c in set(
        [z['country'] for z in zone_data['items']])]
    countries_updated = 'COUNTRIES = ['
    for z in countries_list:
        if z != countries_list[-1]:
            countries_updated += z + ", "
        else:
            countries_updated += z
    countries_updated += ']'
    replace_in_file(input_file, 'COUNTRIES', countries_updated)


def replace_in_file(file_path, pattern, new_line):
    """
    Replace a line in a file if the line contains
    the pattern
    """
    # create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh, 'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                if pattern in line:
                    new_file.write(new_line)
                else:
                    new_file.write(line)
    # copy the file permissions from the old file to the new file
    copymode(file_path, abs_path)
    remove(file_path)
    move(abs_path, file_path)

if __name__ == '__main__':
    dry_run=False
    update_local_database()

    if not dry_run:
        regenerate_firebase_data()