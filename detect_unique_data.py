from enum import Enum
import json
import re
import math

def get_data_local():
    """
    Get data from local files
    """
    video_data = {}
    with open('data/channel/processed_data.json', 'r', encoding='utf-8') as f:
        video_data = json.load(f)['items']
    return video_data

if __name__ == '__main__':
    video_data = get_data_local()
    
    unique_zones = set()
    unique_climbers = set()
    
    for video in video_data:
        climber = video["climber"]
        if climber not in unique_climbers:
            unique_climbers.add(climber)
            
        zone = video["zone"]
        if zone not in unique_zones:
            unique_zones.add(zone)
            
    unique_data = {
        "unique_climbers": sorted(unique_climbers),
        "unique_zones": sorted(unique_zones)
    }
    with open('data/channel/unique_data.json', 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, indent=4)        
    
