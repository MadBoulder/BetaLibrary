import json
import handle_channel_data
import utils.helpers
from slugify import slugify
from collections import Counter


def main():
    zones_data = handle_channel_data.get_zone_data()
    existing_zone_codes = {zone['zone_code'] for zone in zones_data['items']}

    video_data = handle_channel_data.get_video_data()

    zone_code_counts = Counter()
    for video in video_data['items']:
        zone_code = video['zone_code']
        if zone_code not in existing_zone_codes:
            zone_code_counts[video['zone_code']] += 1
    
    sorted_zone_code_counts = sorted(zone_code_counts.items(), key=lambda item: item[1], reverse=True)
    for zone_code, count in sorted_zone_code_counts:
        print(f'{zone_code}: {count}')


if __name__ == "__main__":
    main()