from enum import Enum
import urllib.request
import urllib.parse
import json
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
from dotenv import load_dotenv
from functools import lru_cache
import datetime
import utils.channel
import utils.database
import utils.MadBoulderDatabase
import logging

load_dotenv()

ENCODING = 'utf-8'
CONFIG_FILE = 'config.py'


class Case(Enum):
    lower = 1
    upper = 2
    none = 3


def retrieveVideosFromChannel(lastUpdate=None):
    print("Retrieving videos from channel")
    
    try:
        videoNum = utils.channel.fetchChannelTotalVideoCount()
        uploadPLaylistId = utils.channel.getUploadPlaylistId()
        videos = {}
        page_token=None

        while True:
            print(str(round((len(videos)/videoNum)*100, 2))+'%')

            if lastUpdate:
                searchResp = utils.channel.fetchVideoByDate(lastUpdate, page_token)
                videoIds = [item['id']['videoId'] for item in searchResp['items']]
            else:
                searchResp = utils.channel.fetchAllVideoIds(uploadPLaylistId, page_token)
                videoIds = [item['contentDetails']['videoId'] for item in searchResp['items']]

            if videoIds:
                videosResponse = utils.channel.fetchVideoDetails(videoIds)
                for item in videosResponse['items']:
                    videoId = item['id']
                    title = item['snippet']['title']
                    description = item['snippet']['description']
                    videoInfo = ExtractInfoFromDescription(title, description)
                    videos[encodeSlug(videoInfo['secure_slug'])] = {
                        'title': title,
                        'id': videoId,
                        'date': item['snippet']['publishedAt'],
                        'viewCount': item['statistics'].get('viewCount', '0'),
                        **videoInfo
                    }

            page_token = searchResp.get('nextPageToken')
            if not page_token:
                break

        return videos
    except Exception as e:
        logging.error(f"Failed to retrieve videos: {str(e)}")
        return None
    

def encodeSlug(key):
    return key.replace('/', '___')

def decodeSlug(key):
    return key.replace('___', '/')


def retrieve_playlists_from_channel():
    playlists = []
    next_page_token = None

    while True:
        response = utils.channel.fetchPlaylists(next_page_token)
        playlists.extend(response["items"])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    print('Playlists retrieved: ' + str(len(playlists)))
    return playlists


def updateVideosFromChannel():
    updatedVideos = updateVideoDatabase()

    dateSinceLastUpdate = getLastDatabaseVideoUpdateDate().isoformat() + "Z"
    newVideos = retrieveVideosFromChannel(dateSinceLastUpdate)
        
    allVideos = {**updatedVideos, **newVideos}
    return allVideos


def updateVideoDatabase():
    print("updateVideoDatabase")

    videos = get_video_data()
    if not videos:
        print("No videos found in database.")
        return None
    
    print("video count", len(videos))
    updatedVideos = {}

    video_ids = [video['id'] for video in videos.values()]
    chunks = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]

    for chunk_index, chunk in enumerate(chunks):
        print(f"Processing batch {chunk_index+1}/{len(chunks)}")
        
        videoResponses = utils.channel.fetchVideoDetails(chunk)
        
        for videoResponse in videoResponses.get('items', []):
            videoId = videoResponse['id']
            videoDetails = videoResponse
            status = videoDetails['status']['privacyStatus']

            corresponding_video = next((v for v in videos.values() if v['id'] == videoId), None)
            if not corresponding_video:
                continue

            videoSlug = corresponding_video['secure_slug']

            if(status == 'public'):
                title = videoDetails['snippet']['title']
                description = videoDetails['snippet']['description']
                newVideoInfo = ExtractInfoFromDescription(title, description)

                if videoSlug != newVideoInfo['secure_slug']:
                    print(videoSlug)
                    print(newVideoInfo['secure_slug'])
                    print(f"Video with ID {videoId} has changed its url.")
                    deprecateSlug(videoSlug, newVideoInfo['secure_slug'])

                updatedVideo = {
                    'title': title,
                    'id': videoId,
                    'date': videoDetails['snippet']['publishedAt'],
                    'viewCount': videoDetails['statistics'].get('viewCount', '0'),
                    **newVideoInfo
                }
                updatedVideos[encodeSlug(newVideoInfo['secure_slug'])] = updatedVideo
            else:
                print(f"Video with ID {videoId} not public.")
                disableSlug(videoSlug)
                updatedVideos[videoSlug] = None
        
        
    print(f"Updated videos count: {len(updatedVideos)}")
    return updatedVideos


def getLastDatabaseVideoUpdateDate():
    print("getLastDatabaseVideoUpdateDate")
    lastUpdate = utils.database.getValue('video_data/date')
    print(lastUpdate)       
    if lastUpdate: 
        return datetime.datetime.strptime(lastUpdate, '%Y-%m-%d')
    else:
        return datetime.datetime.now()


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
    }

    videoInfo['name'] = getProblemName(title, videoInfo['name'], videoInfo['grade'], videoInfo['zone'])
    videoInfo['zone_code'] = slugify(videoInfo['zone'])
    videoInfo['secure_slug'] = videoInfo['zone_code'] + '/' + slugify(videoInfo['name'] + '-'+ videoInfo['grade_with_info'])
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


def updateData(
    retrieve_data_from_channel=True
):
    if retrieve_data_from_channel:
        retrieveAndUpdateVideoData(resetDatabase=False)
        createOptimizedVideoData()
        retrieveAndUpdatePlaylistData()
    updateZoneData()
    updateCountries()
    updateBoulderData()
    updateContributorsList()


def retrieveAndUpdateVideoData(resetDatabase=False):
    video_data = []
    if resetDatabase:
        print("Regenerating video database")
        video_data = retrieveVideosFromChannel()
    else:
        print("Updating video databse")
        video_data = updateVideosFromChannel()

    if video_data:
        print("Videos Retrived: ", len(video_data))
        utils.database.updateNodeWithItems('video_data', video_data, reset=resetDatabase)
        utils.database.updateNode('video_count', len(video_data))
        
        saveDebugJson('video_data.json', video_data)


def createOptimizedVideoData():
    print("createOptimizedVideoData")

    videoData = get_video_data()
    if not videoData:
        print("No video data found.")
        return []

    processed_data_search_optimized = [video for video in videoData.values() if video.get('name') != 'Unknown']
    for video in processed_data_search_optimized:
        del video['viewCount']
        del video['date']
        del video['zone_code']
        del video['climber_code']
        del video['sector_code']
        del video['boulder_code']
    
    utils.database.updateNodeWithItems('video_data_search_optimized', processed_data_search_optimized, reset=True)

    saveDebugJson('processed_data_search_optimized.json', processed_data_search_optimized)

         
def retrieveAndUpdatePlaylistData():
    print("retrieveAndUpdatePlaylistData")
    
    playlists = retrieve_playlists_from_channel()
                   
    saveDebugJson('raw_playlist_data.json', playlists)
    
    processed_playlist_data = []
    print("retrieveAndUpdatePlaylistData Processing..")
    for playlist in playlists:
        title = playlist['snippet']['title']
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
            playlist_json_object['id'] = playlist['id']
            playlist_json_object['video_count'] = playlist['contentDetails']['itemCount']
            playlist_json_object['thumbnail'] = get_playlist_thumbnail(playlist['snippet']['thumbnails'])
        else:
            playlist_json_object['sectors'].append({"name": sector_name, 
                                                    "sector_code": slugify(sector_name), 
                                                    "id": playlist['id'],
                                                    "video_count": playlist['contentDetails']['itemCount']})

    utils.database.updateNodeWithItems('playlist_data', processed_playlist_data, reset=True)

    saveDebugJson('processed_playlist_data.json', processed_playlist_data)


def updateZoneData():
    print("updateZoneData")
    
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
        
        utils.database.updateNodeWithItems('zone_data', zones_data, reset=True)

        saveDebugJson('zone_data.json', zones_data)
   

def updateContributorsList():
    print("updateContributorsList")
    video_data = get_video_data()

    contributors = {}
    slug_cache = {}
    for video, videoInfo in video_data.items():
        print(video)
        climber_name = videoInfo['climber']

        if climber_name in slug_cache:
            climber_code = slug_cache[climber_name]
        else:
            climber_code = slugify(climber_name)
            slug_cache[climber_name] = climber_code

        if climber_code not in contributors:
            contributors[climber_code] = {'name': climber_name, 'videos': {video: videoInfo}, 'view_count': int(videoInfo['viewCount'])}
        else:
            contributors[climber_code]['videos'][video] = videoInfo
            contributors[climber_code]['view_count'] += int(videoInfo['viewCount'])
    
    utils.database.updateNodeWithItems('contributors', contributors, reset=True)
    utils.database.updateNode('contributor_count', len(contributors))


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


def get_video_data():
    return utils.database.getValue('video_data/items')
    
def get_video_data_search_optimized():
    return utils.database.getValue('video_data_search_optimized/items')

def get_contributors_count():
    return utils.database.getValue('contributor_count')

def get_contributors_list():
    print("get_contributors_list")
    return utils.database.getValue('contributors/items')

def get_video_count():
    return utils.database.getValue('video_count')

def get_playlist_data():
    return utils.database.getValue('playlist_data/items')

def get_zone_data():
    return utils.database.getValue('zone_data/items')

def get_country_data():
    return utils.database.getValue('country_data/items')

def get_boulder_data():
    return utils.database.getValue('boulder_data/items')


def updateCountries():
    print("updateCountries")
    countries = {}
    with open('data/countries.json', 'r', encoding='utf-8') as f:
        countries = json.load(f)['items']

    utils.database.updateNodeWithItems('country_data', countries, reset=True)
    updateCountriesConfig()


def updateBoulderData():
    print("updateBoulders")
    boulders = {}
    with open('data/channel/boulder_data.json', 'r', encoding='utf-8') as f:
        boulders = json.load(f)['items']

    utils.database.updateNodeWithItems('boulder_data', boulders, reset=True)


def updateCountriesConfig():
    zone_data = get_zone_data()

    countries_list = [f'\'{c}\'' for c in set(
        [z['country'] for z in zone_data])]
    countries_updated = 'COUNTRIES = ['
    for z in countries_list:
        if z != countries_list[-1]:
            countries_updated += z + ", "
        else:
            countries_updated += z
    countries_updated += ']'
    replace_in_file(CONFIG_FILE, 'COUNTRIES', countries_updated)


def replace_in_file(file_path, pattern, new_line):
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


def deprecateSlug(oldSlug, newSlug):
    utils.MadBoulderDatabase.deprecateSlug(oldSlug, newSlug)

def disableSlug(oldSlug):
    utils.MadBoulderDatabase.disableSlug(oldSlug)


def saveDebugJson(fileName, data):
    with open(f'/data/debug/{fileName}', 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                  'items': data}, f, indent=4)
        

if __name__ == '__main__':
    dry_run=False

    updateData()