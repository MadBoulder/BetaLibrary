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
from collections import Counter


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


def getMissingAreasCount():
    print("get missing areas")
    
    zones_data = utils.MadBoulderDatabase.getAreasData()
    existing_zone_codes = set(zones_data.keys())

    videoData = utils.MadBoulderDatabase.getAllVideoData()

    zone_code_counts = Counter()
    for areaCode, problems in videoData.items():
        if areaCode not in existing_zone_codes:
            zone_code_counts[areaCode] += len(problems)
    
    return sorted(zone_code_counts.items(), key=lambda item: item[1], reverse=True)


def format_views(number):
    if number >= 1_000_000:
        formatted_number = number / 1_000_000
        return f"{formatted_number:.2f}M".rstrip('0').rstrip('.') if formatted_number < 10 else f"{formatted_number:.1f}M".rstrip('0').rstrip('.') if formatted_number < 100 else f"{int(formatted_number)}M"
    elif number >= 1_000:
        formatted_number = number / 1_000
        return f"{formatted_number:.2f}k".rstrip('0').rstrip('.') if formatted_number < 10 else f"{formatted_number:.1f}k".rstrip('0').rstrip('.') if formatted_number < 100 else f"{int(formatted_number)}k"
    else:
        return str(number)



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
