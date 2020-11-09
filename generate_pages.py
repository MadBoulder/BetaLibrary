import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import helpers

LINK_FIELD = 'link'
NAME_FIELD = 'name'
LATITUDE_FIELD = 'latitude'
LONGITUDE_FIELD = 'longitude'
GUIDES_FIELD = 'guides'
PLAYLIST_FIELD = 'playlist'
SECTORS_FIELD = 'sectors'
AFFILIATE_GUIDES = 'affiliate_guides'

def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    areas = next(os.walk('data/zones/'))[1]

    template_loader = FileSystemLoader(searchpath=".")
    template_env = Environment(loader=template_loader)

    playlists = {}
    for area in areas:
        # Create zone map
        print(area)
        datafile = 'data/zones/' + area + '/' + area + '.txt'
        area_data = {}
        with open(datafile, encoding='utf-8') as data:
            area_data = json.load(data)
        # get external guide links
        guides = [(guide[NAME_FIELD], guide[LINK_FIELD])
                  for guide in area_data[GUIDES_FIELD] if guide.get(LINK_FIELD)]
        # get affiliate guides links 
        affiliate_guides = [affiliate_guide[LINK_FIELD] for affiliate_guide in area_data.get(AFFILIATE_GUIDES, [])]

        base_url = "https://www.youtube.com/embed/?listType=playlist&list="
        playlists[area] = area_data[PLAYLIST_FIELD]
        sectors_playlists = [(sector[NAME_FIELD], base_url + sector[LINK_FIELD].split("list=")[1])
                             for sector in area_data[SECTORS_FIELD] if sector[LINK_FIELD]]

        template = template_env.get_template('templates/zone_layout.html')
        output = template.render(
            name=area_data[NAME_FIELD], tag_name=area_data[NAME_FIELD].replace("'", r"\'"), guide_list=guides,
            affiliate_guide_list=affiliate_guides, map_url='maps/'+area, full_playlist=base_url + area_data[PLAYLIST_FIELD],
            playlists=sectors_playlists, lat=area_data[LATITUDE_FIELD], 
            lng=area_data[LONGITUDE_FIELD], zone=area_data[NAME_FIELD])

        with open('templates/zones/'+area+'.html', 'w', encoding='utf-8') as template:
            template.write(output)

    # Update playlists file
    with open('data/playlist.txt', 'w', encoding='utf-8') as playlists_file:
        playlists_file.write(json.dumps(playlists))


if __name__ == '__main__':
    main()
