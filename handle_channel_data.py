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
import utils.MadBoulderDatabase
import utils.helpers
import logging

load_dotenv()

ENCODING = 'utf-8'
CONFIG_FILE = 'config.py'


def updateData(
    retrieve_data_from_channel=True
):
    if retrieve_data_from_channel:
        retrieveAndUpdateVideoData(resetDatabase=False)
        createOptimizedVideoData()
        retrieveAndUpdatePlaylistData()
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
        utils.MadBoulderDatabase.setVideoData(video_data)
        
        saveDebugJson('video_data.json', video_data)


def retrieveVideosFromChannel(lastUpdate=None):
    print("Retrieving videos from channel")
    
    try:
        videoNum = utils.channel.fetchChannelTotalVideoCount()
        uploadPLaylistId = utils.channel.getUploadPlaylistId()
        videos = {}
        page_token=None
        total_videos_retrieved = 0

        while True:
            if videos:
                total_videos_retrieved = 0
                for area in videos.values():
                    total_videos_retrieved += len(area)
            print(str(round(((total_videos_retrieved)/videoNum)*100, 2))+'%')

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
                    videoInfo = utils.helpers.ExtractInfoFromDescription(title, description)

                    zone_code = videoInfo['zone_code']
                    partial_slug = videoInfo['partial_slug']
                    if zone_code not in videos:
                        videos[zone_code] = {}

                    videos[zone_code][partial_slug] = {
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


def updateVideosFromChannel():
    updatedVideos = updateVideoDatabase()

    dateSinceLastUpdate = getLastDatabaseVideoUpdateDate().isoformat() + "Z"
    newVideos = retrieveVideosFromChannel(dateSinceLastUpdate)
    if newVideos:
        for zone_code, videos in newVideos.items():
            if zone_code not in updatedVideos:
                updatedVideos[zone_code] = {}
            updatedVideos[zone_code].update(videos)

    return updatedVideos


def updateVideoDatabase():
    print("updateVideoDatabase")

    videoData = utils.MadBoulderDatabase.getAllVideoData()
    if not videoData:
        print("No videoData found in database.")
        return None
    
    updatedVideos = {}

    video_ids = [video['id'] for area in videoData.values() for video in area.values()]
    print("video count", len(video_ids))

    chunks = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]

    for chunk_index, chunk in enumerate(chunks):
        print(f"Processing batch {chunk_index+1}/{len(chunks)}")
        
        videoResponses = utils.channel.fetchVideoDetails(chunk)
        
        for videoResponse in videoResponses.get('items', []):
            videoId = videoResponse['id']
            videoDetails = videoResponse
            status = videoDetails['status']['privacyStatus']

            corresponding_video = next((video for area in videoData.values() for video in area.values() if video['id'] == videoId), None)
            if not corresponding_video:
                continue

            zone_code = corresponding_video.get('zone_code')
            partial_slug = corresponding_video.get('partial_slug')
            videoSlug = corresponding_video['secure_slug']

            if(status == 'public'):
                title = videoDetails['snippet']['title']
                description = videoDetails['snippet']['description']
                newVideoInfo = utils.helpers.ExtractInfoFromDescription(title, description)

                if videoSlug != newVideoInfo['secure_slug']:
                    print(videoSlug)
                    print(newVideoInfo['secure_slug'])
                    print(f"Video with ID {videoId} has changed its url.")
                    deprecateSlug(videoSlug, newVideoInfo['secure_slug'])

                    if zone_code != newVideoInfo['zone_code']:
                        print(f"Video with ID {videoId} has changed its area.")
                        zone_code = newVideoInfo['zone_code']

                if zone_code not in updatedVideos:
                    updatedVideos[zone_code] = {}

                updatedVideo = {
                    'title': title,
                    'id': videoId,
                    'date': videoDetails['snippet']['publishedAt'],
                    'viewCount': videoDetails['statistics'].get('viewCount', '0'),
                    **newVideoInfo
                }
                updatedVideos[zone_code][newVideoInfo['partial_slug']] = updatedVideo
            else:
                print(f"Video with ID {videoId} not public.")
                disableSlug(videoSlug)
                if zone_code not in updatedVideos:
                    updatedVideos[zone_code] = {}

                updatedVideos[zone_code][partial_slug] = None
        
        
    print(f"Updated videos count: {sum(len(zone) for zone in updatedVideos.values())}")
    return updatedVideos


def getLastDatabaseVideoUpdateDate():
    print("getLastDatabaseVideoUpdateDate")
    lastUpdate = utils.MadBoulderDatabase.getVideoDataDate()
    print(lastUpdate)       
    if lastUpdate:
        return datetime.datetime.strptime(lastUpdate, '%Y-%m-%dT%H:%M:%S.%f')
    else:
        return datetime.datetime.now()


def createOptimizedVideoData():
    print("createOptimizedVideoData")
    
    optimizedSearchData = {}
    
    videoData = utils.MadBoulderDatabase.getAllVideoData()
    if not videoData:
        print("No video data found.")
        return {}
    optimizedSearchData['problems'] = {}
    for area in videoData.values():
        for videoCode, video in area.items():
            if videoCode == 'Unknown':
                continue
            optimizedSearchData['problems'][utils.MadBoulderDatabase.encodeSlug(video['secure_slug'])] = {
            'name': video['name']
        } 

    
    areasData = utils.MadBoulderDatabase.getAreasData()
    optimizedSearchData['areas'] = {}
    for area_code, area in areasData.items():
        optimizedSearchData['areas'][area_code] = {
            'name': area['name'],
            'country': utils.MadBoulderDatabase.getCountryData(area['country'])['name'][0]
        } 
        
    saveDebugJson('processed_data_search_optimized.json', optimizedSearchData)
    utils.MadBoulderDatabase.setVideoDataSearchOptimized(optimizedSearchData)

    

         
def retrieveAndUpdatePlaylistData():
    print("retrieveAndUpdatePlaylistData")
    
    playlists = retrieve_playlists_from_channel()
    saveDebugJson('raw_playlist_data.json', playlists)
    
    processed_playlist_data = {}
    print("retrieveAndUpdatePlaylistData Processing..")
    for playlist in playlists:
        title = playlist['snippet']['title']
        is_sector = ': Sector' in title
        zone_name, sector_name = title.split(': Sector ') if is_sector else (title, None)
        
        zone_code = slugify(zone_name)
        if zone_code not in processed_playlist_data:
            processed_playlist_data[zone_code] = {
                "title": zone_name,
                "zone_code": zone_code,
                "sectors": {}
            }

        if is_sector:
            sector_code = slugify(sector_name)
            processed_playlist_data[zone_code]['sectors'][sector_code] = {
                "name": sector_name,
                "sector_code": sector_code,
                "id": playlist['id'],
                "video_count": playlist['contentDetails']['itemCount'],
                "thumbnails": get_playlist_thumbnails(playlist['snippet']['thumbnails'])
            }
        else:
            processed_playlist_data[zone_code].update({
                "id": playlist['id'],
                "video_count": playlist['contentDetails']['itemCount'],
                "thumbnails": get_playlist_thumbnails(playlist['snippet']['thumbnails'])
            })
        
    utils.MadBoulderDatabase.setPlaylistData(processed_playlist_data)

    saveDebugJson('processed_playlist_data.json', processed_playlist_data)


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

#deprecated
def updateAreaData():
    print("updateZoneData")
    return
    
    zone_data_path = 'data/zones/'
    zones_data = {}
    
    if os.path.exists(zone_data_path):
        zone_directories  = next(os.walk(zone_data_path))[1]
        for zone_code in zone_directories :
            data_file = f'{zone_data_path}{zone_code}/{zone_code}.json'
            print(data_file)
            with open(data_file, encoding='utf-8') as file:
                zone_data = json.load(file)

                zone_data['zone_code'] = slugify(zone_data['name'])
                zone_data['altitude'] = get_altitude_from_coordinates(zone_data['latitude'], zone_data['longitude'])
                zones_data[zone_data['zone_code']] = zone_data
        
        utils.MadBoulderDatabase.setAreaData(zones_data)

        saveDebugJson('zone_data.json', zones_data)
   

def updateContributorsList():
    print("updateContributorsList")
    videoData = utils.MadBoulderDatabase.getAllVideoData()

    contributors = {}
    slug_cache = {}
    for areaCode, area in videoData.items():
        for videoPartialSlug, videoInfo in area.items():
            video_slug = utils.MadBoulderDatabase.createEncodedSlug(areaCode, videoPartialSlug)
            print(video_slug)
            climber_name = videoInfo['climber']

            if climber_name in slug_cache:
                climber_code = slug_cache[climber_name]
            else:
                climber_code = slugify(climber_name)
                slug_cache[climber_name] = climber_code

            if climber_code not in contributors:
                contributors[climber_code] = {'name': climber_name, 'videos': {video_slug: videoInfo}, 'view_count': int(videoInfo['viewCount'])}
            else:
                contributors[climber_code]['videos'][video_slug] = videoInfo
                contributors[climber_code]['view_count'] += int(videoInfo['viewCount'])
    
    saveDebugJson('contributors.json', contributors)
    utils.MadBoulderDatabase.setContributorData(contributors)


def get_playlist_thumbnails(thumbnails):
    return {
        'maxres': thumbnails.get('maxres', {}).get('url'),
        'standard': thumbnails.get('standard', {}).get('url'),
        'high': thumbnails.get('high', {}).get('url'),
        'medium': thumbnails.get('medium', {}).get('url'),
        'default': thumbnails.get('default', {}).get('url')
    }
    
    
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


def updateBoulderData():
    print("updateBoulders")
    with open('data/channel/boulder_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    formatted_boulder_data = {}
    for item in data['items']:
        area_code = item['area_code']
        formatted_boulder_data[area_code] = {}
        for boulder in item['boulders']:
            boulder_code = boulder['name_code']
            formatted_boulder_data[area_code][boulder_code] = {
                'name': boulder['name'],
                'coordinates': boulder['coordinates']
            }

    utils.MadBoulderDatabase.setBoulderData(formatted_boulder_data)

#deprecated
def updateCountries():
    print("updateCountries")
    return
    data = {}
    with open('data/countries.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    formatted_country_data = {}
    for item in data['items']:
        countryCode = item['code']
        formatted_country_data[countryCode] = {
            'reduced_code' : item['reduced_code'],
            'name' : item['name'],
            'overview' : item['overview'],
            'states' : {}
        }

        if item.get('states'):
            for state in item['states']:
                stateCode = state['code']
                formatted_country_data[countryCode]['states'][stateCode] = {
                    'name': state['name']
                }

    utils.MadBoulderDatabase.setCountryData(formatted_country_data)


def deprecateSlug(oldSlug, newSlug):
    utils.MadBoulderDatabase.deprecateSlug(oldSlug, newSlug)

def disableSlug(oldSlug):
    utils.MadBoulderDatabase.addDisableSlug(oldSlug)


def saveDebugJson(fileName, data):
    directory = 'data/debug'
    if not os.path.exists(directory):
        os.makedirs(directory)

    filePath = os.path.join(directory, fileName)
    with open(filePath, 'w', encoding='utf-8') as f:
        json.dump({'date': str(date.today()),
                  'items': data}, f, indent=4)
        

if __name__ == '__main__':
    dry_run=False

    updateData()