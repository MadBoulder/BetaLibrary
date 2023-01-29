import json


def get_problems_from_zone(zone):
    """
    Given a zone name, return all problems we have for that area
    Cache for 24 hours or something like that? - We might have to
    adjust how this gets computed 
    """
    with open('data/channel/processed_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    # process data
    with open(f'data/zones/{zone}/{zone}.json', 'r', encoding='utf-8') as z:
        zone_name = json.load(z)['name']
    # filter data by zone and extract problem name 
    problems = [p for p in data['items'] if p['zone'] == zone_name]
    return problems

if __name__ == "__main__":
    print(len(get_problems_from_zone('albarracin')))
