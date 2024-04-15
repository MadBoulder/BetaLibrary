import json
from slugify import slugify
import handle_channel_data
import utils.database
from functools import lru_cache


def get_zone_view_count_from_zone_code(zone_code):
    problems = utils.database.getVideoDataFromZone(zone_code)
    total_views = sum(int(problem['viewCount']) for problem in problems)
    return total_views


def get_view_count_from_problems(problems):
    total_views = sum(int(problem['viewCount']) for problem in problems)
    return total_views


def get_contributor_count_from_problems(problems):
    contributors = {problem['climber_code'] for problem in problems}
    return len(contributors)


def get_contributor_data(contributor_id):
    contributor = None
    if contributor_id:
        contributor = handle_channel_data.get_contributors_list().get(slugify(contributor_id), None)
    return contributor


def get_problems_from_sector(problems_zone, sector_code):
    problems = []
    for p in problems_zone:
        if slugify(p['sector']) == sector_code:
            problems.append(p)

    return problems
    
    
def get_sectors_from_zone(zone_code):
    problems = utils.database.getVideoDataFromZone(zone_code)
    sectors = []
    for p in problems:
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
    

def get_rock_type_str(rock_type_code):
    rock_type_mapping = {
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
    return rock_type_mapping.get(rock_type_code.lower(), "Unknown")
    
   
def get_playlist_url_from_sector(zone_code, sector):
    playlists = get_playlists_from_zone(zone_code)
    if 'sectors' in playlists:
        for playlist in playlists['sectors']:
            if slugify(playlist['name']) == sector:
                return playlist['url']
    return None
    
    
def get_playlists_from_zone(zone_code):
    playlist_data = handle_channel_data.get_playlist_data()

    playlists = []
    for item in playlist_data:
        if item['zone_code'] == zone_code:
            playlists = item
            break
            
    return playlists


def get_areas_from_country(country_code):
    zone_data = handle_channel_data.get_zone_data()

    areas = []
    for item in zone_data:
        if item['country'] == country_code:
            areas.append(item)
            
    return areas


def get_areas_from_state(state_code):
    zone_data = handle_channel_data.get_zone_data()

    areas = []
    for item in zone_data:
        if item.get('state','') == state_code:
            areas.append(item)
            
    return areas


def get_country_from_code(country_code):
    country_data = handle_channel_data.get_country_data()

    country = {}
    for item in country_data:
        if item['reduced_code'] == country_code:
            country = item
            break
            
    return country


def get_state_from_code(state_code):
    country_data = handle_channel_data.get_country_data()

    state = {}
    for item in country_data:
        states = item.get('states', [])
        for item2 in states:
            if item2['code'] == state_code:
                state = item2
                break
            
    return state


@lru_cache(maxsize=10)
def calculate_contributor_stats(climber_id):
    climber_id = slugify(climber_id)
    contributor_data = get_contributor_data(climber_id)
    videos = contributor_data['videos']
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
    contributors = handle_channel_data.get_contributors_list()
    all_stats = [
        {'climber_id': climber_code, 'name': data['name'], 'video_count': len(data['videos']), 'view_count': data['view_count']}
        for climber_code, data in contributors.items()
    ]
    
    rankings_by_videos = sorted(all_stats, key=lambda x: x['video_count'], reverse=True)
    rankings_by_views = sorted(all_stats, key=lambda x: x['view_count'], reverse=True)

    video_rankings = {stat['climber_id']: rank+1 for rank, stat in enumerate(rankings_by_videos)}
    view_rankings = {stat['climber_id']: rank+1 for rank, stat in enumerate(rankings_by_views)}
    

    return video_rankings, view_rankings