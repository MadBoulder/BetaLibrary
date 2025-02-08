import re
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
from slugify import slugify
import utils.drive
from utils.ai_helper import GenerativeAI
from datetime import datetime
from enum import Enum

class Case(Enum):
    lower = 1
    upper = 2
    none = 3

ai = GenerativeAI()

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


def generateDescription(name, climber, grade, zone, sector=None, isShort=False):
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
    
    # Build the full description without extra indentation
    description = f"""{chr(10).join(metadata)}

Is this not the correct line or beta? Please tell us!

Do you have a beta recorded? Share it with us and help all the community. DM us in IG @madboulder for more details or upload it here:  https://www.madboulder.org/upload

➞ {zone} Bouldering https://www.madboulder.org/{zone_code}

➞ VISIT https://www.madboulder.org and discover all our content!

➞ SUBSCRIBE to MadBoulder: https://www.youtube.com/c/MadBoulder

Do you enjoy our content? Please consider supporting what we do:
➞ Official Merch Store: https://shop.madboulder.org

#madboulder #bouldering #climbing #boulder #escalada #bloc #bloque #boulderinglife #climbingismypassion #climbinglovers #climbingworldwide #{zone_code}"""
    
    if isShort:
        description += " #shorts"
    
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


def isVideoShort(file_id):
    """Determine if a video qualifies as a YouTube Short based on its metadata."""
    try:
        metadata = utils.drive.getFileMetadata(file_id)
        if metadata is None:
            print(f"Error: No metadata found for file ID {file_id}.")
            return False
        
        video_metadata = metadata.get('videoMediaMetadata', {})
        if not video_metadata:
            print(f"Error: No video media metadata found for file ID {file_id}.")
            return False
        
        duration_millis = video_metadata.get('durationMillis', 0)
        duration_seconds = int(duration_millis) / 1000
        
        width = int(video_metadata.get('width', 0))
        height = int(video_metadata.get('height', 0))
        print(f"Duration: {duration_seconds} seconds, Width: {width}, Height: {height}")
        
        aspect_ratio = (height / width) if width > 0 else 0
        is_vertical = aspect_ratio >= 1
        
        # Determine if video qualifies as a YouTube Short
        result = is_vertical and (duration_seconds > 0 and duration_seconds <= 180)
        print(f"Determined short video: {result} (is_vertical: {is_vertical}, duration: {duration_seconds} sec)")
        return result
        
    except Exception as e:
        print(f"Error determining if video is short: {e}")
        return False


def suggestUploadTime(is_short, climber, grade, zone):
    print("suggestUploadTime")
    video_data = {
        'zone': zone,
        'grade': grade,
        'is_short': is_short,
        'climber': climber
    }
    scheduled_videos = utils.channel.getScheduledVideos()
    recommendation = ai.get_schedule_recommendation(video_data, scheduled_videos)

    schedule_info = None
    if recommendation and 'recommended_hour' in recommendation and 'recommended_date' in recommendation:
        recommended_date = datetime.strptime(recommendation['recommended_date'], '%Y-%m-%d')
        utc_time = recommended_date.replace(
            hour=recommendation['recommended_hour'],  # Already in UTC
            minute=0,
            second=0
        )
        schedule_info = {
            'success': True,
            'scheduled_time': utc_time.strftime("%Y-%m-%d %H:%M:%S"),
            'reasoning': recommendation['reasoning']
        }
    else:
        schedule_info = {
            'success': False,
            'message': 'Could not determine schedule time'
        }

    return schedule_info


def ExtractFieldFromStr(pattern, sourceStr, case=Case.none):
    """
    Given a regex pattern and a field, find the sequence that matches
    the regex in the specified video field. Add the matched sequence as
    the specified new video field
    """
    reg_pattern = re.compile(pattern)
    resultStr = ''
    if sourceStr:
        matches = reg_pattern.findall(sourceStr)
        if not matches:
            resultStr = 'Unknown'
        elif case == Case.upper:
            resultStr = matches[0].upper()
        elif case == Case.lower:
            resultStr = matches[0].lower()
        else:
            resultStr = matches[0]
    return resultStr


def ExtractInfoFromDescription(title, description):
    videoInfo = {
        'name': ExtractName(description),
        'grade': ExtractGrade(description),
        'grade_with_info': ExtractGradeWithInfo(description),
        'climber': ExtractClimber(description),
        'zone': ExtractZone(description),
        'sector': ExtractSector(description),
        'boulder': ExtractBoulder(description),
        'isShort': False 
    }

    # Set isShort to True if '#shorts' hashtag is found in the description
    if '#shorts' in description.lower():
        videoInfo['isShort'] = True

    videoInfo['name'] = getProblemName(title, videoInfo['name'], videoInfo['grade'], videoInfo['zone'])
    videoInfo['zone_code'] = slugify(videoInfo['zone'])
    videoInfo['partial_slug'] = slugify(videoInfo['name'] + '-'+ videoInfo['grade_with_info'])
    videoInfo['secure_slug'] = videoInfo['zone_code'] + '/' + videoInfo['partial_slug']
    videoInfo['sector_code'] = slugify(videoInfo['sector'])
    videoInfo['climber_code'] = slugify(videoInfo['climber'])
    videoInfo['boulder_code'] = slugify(videoInfo['boulder'])

    return videoInfo

def ExtractName(sourceStr):
    name_regex = r'Name: \s*?(.*?)(?:\n|$)'
    return ExtractFieldFromStr(name_regex, sourceStr)

def ExtractGrade(sourceStr):
    regex = r'Grade:\s*(.+?)(?:\s*\([^)]*\))?(?:\n|$)'
    return ExtractFieldFromStr(regex, sourceStr)

def ExtractGradeWithInfo(sourceStr):
    regex = r'Grade: \s*?(.*?)(?:\n|$)'
    return ExtractFieldFromStr(regex, sourceStr)

def ExtractClimber(sourceStr):
    regex = r'Climber: \s*?(.*?)(?:\n|$)'
    return ExtractFieldFromStr(regex, sourceStr)

def ExtractZone(sourceStr):
    regex = r'Zone: \s*?(.*?)(?:\n|$)'
    return ExtractFieldFromStr(regex, sourceStr)

def ExtractSector(sourceStr):
    regex = r'Sector: \s*?(.*?)(?:\n|$)'
    return ExtractFieldFromStr(regex, sourceStr)

def ExtractBoulder(sourceStr):
    regex = r'\bBoulder:\s*([^\n]+)'
    return ExtractFieldFromStr(regex, sourceStr)


def getProblemName(title, nameDescription, grade, zone):
    name = nameDescription
    if name == 'Unknown':
        name = title.replace(
            zone, ''
        ).replace(
            grade.lower(), ''
        ).replace(
            grade.upper(), ''
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