import urllib.request
import urllib.parse
import json
import os
import os.path
import time
from datetime import date
import re

MAX_ITEMS_API_QUERY = 50


def get_channel_info(channel_id="UCX9ok0rHnvnENLSK7jdnXxA"):
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


def get_videos_from_channel(channel_id="UCX9ok0rHnvnENLSK7jdnXxA", num_videos=MAX_ITEMS_API_QUERY, page_token=None):
    """
    Get the title, description and id of all the videos uploaded to a channel
    """
    api_key = None
    with open('credentials.txt', 'r', encoding='utf-8') as f:
        api_key = f.read()

    url = "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={}&key={}".format(
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

        get_videos_url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults={}&playlistId={}&key={}".format(
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
            videos.append(v_data)

        progress += 50

        if resp.get('nextPageToken', False):
            page_token = resp.get('nextPageToken')

    return videos


def update_videos_from_channel(channel_id="UCX9ok0rHnvnENLSK7jdnXxA", num_videos=MAX_ITEMS_API_QUERY, infile='data/channel/raw_video_data.json', page_token=None):
    # compare number of videos
    video_data = []
    with open(infile, 'r', encoding='utf-8') as f:
        try:
            video_data = json.load(f)['items']
        except:
            pass

    video_ids = [v['id'] for v in video_data]

    total_video_count = int(
        get_channel_info()['items'][0]['statistics']['videoCount'])
    if len(video_data) >= total_video_count:
        print('Already up to date')
        return video_data
    # there are new videos, get them
    api_key = None
    with open('credentials.txt', 'r', encoding='utf-8') as f:
        api_key = f.read()

    url = "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={}&key={}".format(
        channel_id, api_key
    )
    inp = urllib.request.urlopen(url)
    resp = json.load(inp)
    upload_playlist = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    missing_videos = total_video_count - len(video_data)
    progress = 0
    new_videos = []
    while progress < missing_videos:
        print(str(round((progress/missing_videos)*100, 2)) + '%')

        get_videos_url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults={}&playlistId={}&key={}".format(
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
                v_data['description'] = video['snippet']['description']
                v_data['id'] = video['snippet']['resourceId']['videoId']
                v_data['url'] = get_video_url_from_id(v_data['id'])
                new_videos.append(v_data)

        progress = len(new_videos)

        if resp.get('nextPageToken', False):
            page_token = resp.get('nextPageToken')
    return new_videos + video_data


def get_video_url_from_id(video_id):
    return 'https://www.youtube.com/watch?v={}'.format(video_id)


def load_data(infile=None, data=None):
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
    reg_pattern = re.compile(pattern)
    for video in video_data:
        matches = reg_pattern.findall(video[infield])
        if matches:
            video[outfield] = matches[0]
        else:
            video[outfield] = 'Unknown'
    return video_data


def process_grade_data(infile=None, data=None):
    video_data = load_data(infile, data)
    # This regex only matches french grades.
    grade_regex = ', (\d{1}[A-Za-z]?\+?\-?\??(?:\/\d?\w?\+?)?)(?: \(sit\))?(?: \(trav\))?(?: \(stand\))?\.? '
    return match_regex_and_add_field(grade_regex, 'title', 'grade', video_data)


def process_climber_data(infile=None, data=None):
    video_data = load_data(infile, data)
    # regex to match climbers.
    climber_regex = '(?:Climber: ?)(@?\w+ ?(?:\w+)?)'
    return match_regex_and_add_field(climber_regex, 'description', 'climber', video_data)


def process_zone_data(infile=None, data=None):
    video_data = load_data(infile, data)
    # regex to match zones.
    zone_regex = '(?:\.+.+)?(?:\. )(.+)$'
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


def get_channel_data(outfile='data/channel/raw_video_data.json', is_update=True):
    if is_update:
        video_data = update_videos_from_channel(page_token=None)
    else:
        video_data = get_videos_from_channel(page_token=None)

    with open(outfile, 'w', encoding='utf-8') as f:
        print('Videos retrieved: ' + str(len(video_data)))
        json.dump({'date': str(date.today()),
                   'items': video_data}, f, indent=4)

    processed_data = process_grade_data(
        infile='data/channel/raw_video_data.json')
    processed_data = process_climber_data(data=processed_data)
    processed_data = process_zone_data(data=processed_data)

    with open('data/channel/processed_data.json', 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                   'items': processed_data}, f, indent=4)

    return {'date': str(date.today()), 'items': processed_data}


if __name__ == "__main__":
    get_channel_data()
