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
from textwrap import dedent
from slugify import slugify


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


def generateDescription(name, climber, grade, zone, sector=None):
    """Generate standardized video description with metadata and links"""
    zone_code = slugify(zone)
    
    # Build metadata section
    metadata = [
        f"Climber: {climber}",
        f"Name: {name}",
        f"Grade: {grade}",
        f"Zone: {zone}"
    ]
    if sector:
        metadata.append(f"Sector: {sector}")
    
    # Build the full description
    description = dedent(f"""
        {chr(10).join(metadata)}

        Is this not the correct line or beta? Please tell us!

        Do you have a beta recorded? Share it with us and help all the community. DM us in IG @madboulder for more details or upload it here:  https://www.madboulder.org/upload

        ➞ {zone} Bouldering https://www.madboulder.org/{zone_code}

        ➞ VISIT https://www.madboulder.org and discover all our content!

        ➞ SUBSCRIBE to MadBoulder: https://www.youtube.com/c/MadBoulder

        Do you enjoy our content? Please consider supporting what we do:
        ➞ Official Merch Store: https://shop.madboulder.org

        #madboulder #bouldering #climbing #boulder #escalada #bloc #bloque #boulderinglife #climbingismypassion #climbinglovers #climbingworldwide #{zone_code}
    """).strip()
    
    return description


def generateTags(name, zone, grade):
    """Generate standardized video tags"""
    return [
        "madboulder", "boulder", "bouldering", "escalada", "climbing", "bloc",
        "escalade", "climb", "climber", "mad boulder", "bloque", "klettern",
        "arrampicata", "boulder beta", "beta library", "escalada en roca",
        "rock climbing", f"{zone} Boulder", f"{zone} bouldering", f"{zone} {grade}",
        f"{zone}", f"{zone} climbing", f"{name} {grade}", f"{name} {grade} {zone}",
        f"{name} {zone}", f"{name}"
    ]
