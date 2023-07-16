import os
from jinja2 import Environment, FileSystemLoader
import json
import utils.helpers
import utils.zone_helpers
import handle_channel_data
from werkzeug.utils import secure_filename
from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove

LINK_FIELD = 'link'
NAME_FIELD = 'name'
LATITUDE_FIELD = 'latitude'
LONGITUDE_FIELD = 'longitude'
GUIDES_FIELD = 'guides'
PLAYLIST_FIELD = 'playlist'
SECTORS_FIELD = 'sectors'
AFFILIATE_GUIDES = 'affiliate_guides'
COUNTRY_FIELD = 'country'
CONFIG_FILE = 'config.py'

# When generating pages because a new zone has been added,
# also update the list of zones in the database


def set_zones_to_firebase(zone_data):
    """
    zone: {
        normalized_name,
        name,
        videos,
        playlist,
        country,
    }
    """
    handle_channel_data.set_zone_data(zone_data)


def update_countries_list(zones, input_file=CONFIG_FILE):
    """
    Update the current list of countries where 
    we have bouldering zones
    """
    # TODO: If a location has no country set, 
    # this function should fallback and compute it
    # Update contries list
    countries_list = [f'\'{c}\'' for c in set(
        [z[COUNTRY_FIELD] for z in zones])]
    countries_updated = 'COUNTRIES = ['
    for z in countries_list:
        if z != countries_list[-1]:
            countries_updated += z + ", "
        else:
            countries_updated += z
    countries_updated += ']'
    replace_in_file(input_file, 'COUNTRIES', countries_updated)


def replace_in_file(file_path, pattern, new_line):
    """
    Replace a line in a file if the line contains
    the pattern
    """
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


def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    areas = next(os.walk('data/zones/'))[1]

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    playlists = {}
    zones = list()
    for area in areas:
        # Create zone map
        print(area)
        datafile = 'data/zones/' + area + '/' + area + '.json'
        area_data = {}
        with open(datafile, encoding='utf-8') as data:
            area_data = json.load(data)
        # get external guide links
        guides = [(guide[NAME_FIELD], guide[LINK_FIELD])
                  for guide in area_data[GUIDES_FIELD] if guide.get(LINK_FIELD)]
        # get affiliate guides links
        affiliate_guides = [affiliate_guide[LINK_FIELD]
                            for affiliate_guide in area_data.get(AFFILIATE_GUIDES, [])]

        base_url = 'https://www.youtube.com/embed/?listType=playlist&list='
        playlists[area] = area_data[PLAYLIST_FIELD]
        sectors_playlists = [(sector[NAME_FIELD], base_url + sector[LINK_FIELD].split('list=')[1])
                             for sector in area_data[SECTORS_FIELD] if sector[LINK_FIELD]]

        # problems
        problems = utils.zone_helpers.get_problems_from_zone(area)
        for p in problems:
            p['secure'] = secure_filename(p['name'])

        # sort alphabetically
        problems.sort(key= lambda x: x['name'])

        template = template_env.get_template('templates/zone_layout.html')
        output = template.render(
            problems=problems,
            area_code=area,
            name=area_data[NAME_FIELD],
            file_name=area,
            tag_name=area_data[NAME_FIELD].replace("'", r"\'"),
            guide_list=guides,
            affiliate_guide_list=affiliate_guides,
            map_url='maps/'+area,
            full_playlist=base_url + area_data[PLAYLIST_FIELD],
            playlists=sectors_playlists,
            lat=area_data[LATITUDE_FIELD],
            lng=area_data[LONGITUDE_FIELD],
            zone=area_data[NAME_FIELD],
            layout_css='static/css/layout.css')

        with open('templates/zones/'+area+'.html', 'w', encoding='utf-8') as template:
            template.write(output)

    # Update playlists file
    with open('data/playlist.json', 'w', encoding='utf-8') as playlists_file:
        playlists_file.write(json.dumps(playlists))

    for area in areas:
        datafile = 'data/zones/' + area + '/' + area + '.json'
        area_data = {}
        with open(datafile, encoding='utf-8') as data:
            area_data = json.load(data)
        # this currently assumes country codes have been added
        num_videos = 0
        try:
            num_videos = utils.helpers.get_number_of_videos_and_views_for_zone(area)
        except Exception as e:
            pass
        zone = {
            'normalized_name': area,
            'name': area_data[NAME_FIELD],
            'videos': num_videos,
            'playlist': area_data[PLAYLIST_FIELD],
            'country': area_data[COUNTRY_FIELD]
        }
        zones.append(zone)

    # Update countries list
    update_countries_list(zones)

    # Update zones in DDBB
    set_zones_to_firebase(zones)


if __name__ == '__main__':
    main()
