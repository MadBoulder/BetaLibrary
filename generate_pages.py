import os
from jinja2 import Environment, FileSystemLoader
import json
import utils.helpers
import utils.zone_helpers
import handle_channel_data
from slugify import slugify

LINK_FIELD = 'link'
NAME_FIELD = 'name'
ZONE_CODE_FIELD = 'zone_code'
LATITUDE_FIELD = 'latitude'
LONGITUDE_FIELD = 'longitude'
ALTITUDE_FIELD = 'altitude'
GUIDES_FIELD = 'guides'
SECTORS_FIELD = 'sectors'
LINKS_FIELD = 'links'
COUNTRY_CODE_FIELD = 'country'
STATE_CODE_FIELD = 'state'
ROCK_TYPE_FIELD = 'rock_type'
OVERVIEW_FIELD = 'overview'


def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    areas = handle_channel_data.get_zone_data()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    playlists = {}
    for area in areas['items']:
        print("Creating zone map of " + area[NAME_FIELD])
        # get external links
        links = [link for link in area.get(LINKS_FIELD, []) if link.get(LINK_FIELD)]
        # get external guides
        guides = [guide for guide in area.get(GUIDES_FIELD, []) if guide.get(LINK_FIELD)]

        # problems
        problems = utils.zone_helpers.get_problems_from_zone_code(area[ZONE_CODE_FIELD])
        problems.sort(key= lambda x: x['name'])
        for p in problems:
            p['secure'] = slugify(p['name'])
            
        # sectors
        sectors = utils.zone_helpers.get_sectors_from_zone(area[ZONE_CODE_FIELD])
        sectors.sort(key= lambda x: x)
        
        #playlists
        playlists = utils.zone_helpers.get_playlists_from_zone(area[ZONE_CODE_FIELD])

        #country
        country = utils.zone_helpers.get_country_from_code(area[COUNTRY_CODE_FIELD])
        country_name = country.get('name','')[0] if country else ''

        state = utils.zone_helpers.get_state_from_code(area.get(STATE_CODE_FIELD,''))
        state_code = state.get('code','') if state else ''
        state_name = state.get('name','')[0] if state else ''

        #overview
        overview = area.get("overview", [""])[0]
        
        template = template_env.get_template('templates/templates/area-layout.html')
        output = template.render(
            problems=problems,
            sectors=sectors,
            area_code=area[ZONE_CODE_FIELD],
            name=area[NAME_FIELD],
            rock_type=utils.zone_helpers.get_rock_type_str(area.get(ROCK_TYPE_FIELD, "")),
            overview=overview,
            file_name=area[ZONE_CODE_FIELD],
            tag_name=area[NAME_FIELD].replace("'", r"\'"),
            links_list=links,
            guides_list=guides,
            map_url='maps/'+area[ZONE_CODE_FIELD],
            playlists=playlists,
            lat=area[LATITUDE_FIELD],
            lng=area[LONGITUDE_FIELD],
            alt=int(area.get(ALTITUDE_FIELD,'0')),
            zone=area[NAME_FIELD],
            country_code=country.get('code',''),
            country_name=country_name,
            state_code=state_code,
            state_name=state_name
        )

        with open('templates/zones/'+area[ZONE_CODE_FIELD]+'.html', 'w', encoding='utf-8') as template:
            template.write(output)


if __name__ == '__main__':
    main()
