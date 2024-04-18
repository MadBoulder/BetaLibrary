from enum import Enum
import json
import re
import math
import utils.MadBoulderDatabase


if __name__ == '__main__':
    video_data = utils.MadBoulderDatabase.getVideoData()
    
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
    
