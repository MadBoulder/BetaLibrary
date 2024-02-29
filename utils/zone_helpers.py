import json
from slugify import slugify
import handle_channel_data


def get_problems_from_zone_code(zone_code):
    with open(f'data/zones/{zone_code}/{zone_code}.json', 'r', encoding='utf-8') as z:
        zone_name = json.load(z)['name']
    return get_problems_from_zone_name(zone_name)
    
    
def get_problems_from_zone_name(zone_name):
    with open('data/channel/processed_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    # filter data by zone and extract problem name
    problems = [p for p in data['items'] if p['zone'] == zone_name]
    return problems
    
def get_zone_view_count(zone_name):
    problems = get_problems_from_zone_name(zone_name)
    total_views = sum(int(problem['stats']['viewCount']) for problem in problems)
    return total_views
    
def get_zone_view_count_from_zone_code(zone_code):
    problems = get_problems_from_zone_code(zone_code)
    total_views = sum(int(problem['stats']['viewCount']) for problem in problems)
    return total_views
    
    
def get_problems_from_sector(problems_zone, sector_code):
    problems = []
    for p in problems_zone:
        if slugify(p['sector']) == sector_code:
            problems.append(p)

    return problems
    
    
def get_sectors_from_zone(zone_code):
    problems = get_problems_from_zone_code(zone_code)
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
        "grit": "Gritstone"
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
    for item in playlist_data['items']:
        if item['zone_code'] == zone_code:
            playlists = item
            break
            
    return playlists


def get_areas_from_country(country_code):
    zone_data = handle_channel_data.get_zone_data()

    areas = []
    for item in zone_data['items']:
        if item['country'] == country_code:
            areas.append(item)
            
    return areas


def get_areas_from_state(state_code):
    zone_data = handle_channel_data.get_zone_data()

    areas = []
    for item in zone_data['items']:
        if item.get('state','') == state_code:
            areas.append(item)
            
    return areas


def get_country_from_code(country_code):
    country_data = handle_channel_data.get_country_data()

    country = {}
    for item in country_data['items']:
        if item['reduced_code'] == country_code:
            country = item
            break
            
    return country


def get_state_from_code(state_code):
    country_data = handle_channel_data.get_country_data()

    state = {}
    for item in country_data['items']:
        states = item.get('states', [])
        for item2 in states:
            if item2['code'] == state_code:
                state = item2
                break
            
    return state

