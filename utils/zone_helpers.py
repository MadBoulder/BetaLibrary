import json
from slugify import slugify
import utils.MadBoulderDatabase
from functools import lru_cache


def get_view_count_from_problems(problems):
    total_views = sum(int(problem['viewCount']) for problem in problems)
    return total_views


def get_contributor_count_from_problems(problems):
    contributors = {problem['climber_code'] for problem in problems}
    return len(contributors)


def get_contributor_data(contributor_id):
    contributor = None
    if contributor_id:
        contributor = utils.MadBoulderDatabase.getContributorsList().get(slugify(contributor_id), None)
    return contributor


def get_problems_from_sector(problems_zone, sector_code):
    problems = []
    for p in problems_zone.values():
        if slugify(p['sector']) == sector_code:
            problems.append(p)

    return problems
    
    
def get_sectors_from_zone(zone_code):
    problems = utils.MadBoulderDatabase.getVideoDataFromZone(zone_code)
    return getSectors(problems)

def getSectors(problems):
    sectors = []
    for p in problems.values():
        alreadyAdded=False
        for s in sectors:
            if s[1] == slugify(p['sector']):
                alreadyAdded=True
                s[2] += 1
                break
        if not alreadyAdded:
            sectors.append([p['sector'], slugify(p['sector']), 1])
            
    if len(sectors) == 1:
        if sectors[0] == "Unknown":
            return None
    return sectors
    

def getRockTypeList():
    rockTypeMapping = {
        "volc": "Volcanic",
        "lime": "Limestone",
        "gran": "Granite",
        "sand": "Sandstone",
        "cong": "Conglomerate",
        "gnei": "Gneiss",
        "igne": "Igneous",
        "basa": "Basalt",
        "slat": "Slate",
        "schi": "Schist",
        "quar": "Quartzite",
        "iron": "Iron Rock",
        "serp": "Serpentine",
        "grit": "Gritstone",
        "diab": "Diabase"
    }
    return rockTypeMapping


def getRockTypeStr(rock_type_code):
    rockTypeMapping = getRockTypeList()
    return rockTypeMapping.get(rock_type_code.lower(), "Unknown")
    
   
def get_playlist_url_from_sector(zone_code, sector):
    playlists = get_playlists_from_zone(zone_code)
    if 'sectors' in playlists:
        for playlist in playlists['sectors']:
            if slugify(playlist['name']) == sector:
                return playlist['url']
    return None
    
    
def get_playlists_from_zone(zone_code):
    return utils.MadBoulderDatabase.getPlaylistData(zone_code)


def get_areas_from_country(country_code, zone_data):
    areas = {}
    for key, item in zone_data.items():
        if item['country'] == country_code:
            areas[key] = item
            
    return areas


def get_areas_from_state(state_code, zone_data):
    areas = {}
    for key, item in zone_data.items():
        if item.get('state','') == state_code:
            areas[key] = item
            
    return areas


def getStateAndCountryInfoFromData(areasData, countriesData, areaCode):
    countryName = []
    countryCode = ''
    state_name = []
    stateCode = ''
    zoneAdded = False
    
    if areaCode in areasData:
        zoneAdded = True
        countryCode = areasData[areaCode].get('country','')
        if countryCode in countriesData:
            countryName = countriesData[countryCode].get('name',[])
            stateCode = areasData[areaCode].get('state','')
            if 'states' in countriesData[countryCode] and stateCode in countriesData[countryCode]['states']:
                state_name = countriesData[countryCode]['states'][stateCode].get('name',[])

    return {
        'country_name': countryName,
        'country_code': countryCode,
        'state_name': state_name,
        'state_code': stateCode,
        'zone_added': zoneAdded
    }


def getStateAndCountryInfo(areaCode):
    countryName = []
    countryCode = ''
    state_name = []
    stateCode = ''
    
    areaData = utils.MadBoulderDatabase.getAreaData(areaCode)
    if areaData:
        countryCode = areaData.get('country','')
        country = utils.MadBoulderDatabase.getCountryData(countryCode)
        if country:
            countryName = country.get('name',[])
            stateCode = areaData.get('state','')
            state = get_state_in_country(country, stateCode)
            if state:
                state_name = state.get('name',[])

    return {
        'country_name': countryName,
        'country_code': countryCode,
        'state_name': state_name,
        'state_code': stateCode,
        'zone_added': bool(areaData)
    }


def get_country_from_code(country_code):
    country_data = utils.MadBoulderDatabase.getCountriesData()

    for key, item in country_data.items():
        if item['reduced_code'] == country_code:
            return item


@lru_cache(maxsize=10)
def calculate_contributor_stats(climber_id):
    climber_id = slugify(climber_id)
    contributor_data = get_contributor_data(climber_id)
    if contributor_data:
        videos = contributor_data.get('videos')
        unique_areas = set()
        area_counts = {}

        for video in videos.values():
            area = video['zone']
            grade = video['grade']
            unique_areas.add(area)

            if area in area_counts:
                area_counts[area] += 1
            else:
                area_counts[area] = 1

        top_areas = sorted(area_counts.items(), key=lambda x: x[1], reverse=True)
        video_rankings, view_rankings = calculate_rankings()
        user_video_rank = video_rankings.get(climber_id, "Not ranked")
        total_views_rank = view_rankings.get(climber_id, "Not ranked")

        contributor_stats = {
            'num_videos': len(videos),
            'user_video_rank': user_video_rank,
            'total_views': sum(int(video['viewCount']) for video in videos.values()),
            'total_views_rank': total_views_rank,
            'unique_areas': len(unique_areas),
            'top_areas': [{'area': area, 'videos': count} for area, count in top_areas]
        }

        return contributor_stats


@lru_cache(maxsize=10)
def calculate_rankings():
    contributors = utils.MadBoulderDatabase.getContributorsList()
    all_stats = [
        {'climber_id': climber_code, 'name': data['name'], 'video_count': len(data['videos']), 'view_count': data['view_count']}
        for climber_code, data in contributors.items()
    ]
    
    rankings_by_videos = sorted(all_stats, key=lambda x: x['video_count'], reverse=True)
    rankings_by_views = sorted(all_stats, key=lambda x: x['view_count'], reverse=True)

    video_rankings = {stat['climber_id']: rank+1 for rank, stat in enumerate(rankings_by_videos)}
    view_rankings = {stat['climber_id']: rank+1 for rank, stat in enumerate(rankings_by_views)}
    

    return video_rankings, view_rankings