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
GUIDES_FIELD = 'guides'
SECTORS_FIELD = 'sectors'
AFFILIATE_GUIDES = 'affiliate_guides'


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
        # get external guide links
        guides = [(guide[NAME_FIELD], guide[LINK_FIELD])
                  for guide in area.get(GUIDES_FIELD, []) if guide.get(LINK_FIELD)]
        # get affiliate guides links
        affiliate_guides = [affiliate_guide[LINK_FIELD]
                            for affiliate_guide in area.get(AFFILIATE_GUIDES, [])]

        # problems
        problems = utils.zone_helpers.get_problems_from_zone(area[ZONE_CODE_FIELD])
        problems.sort(key= lambda x: x['name'])
        for p in problems:
            p['secure'] = slugify(p['name'])
            
        # sectors
        sectors = utils.zone_helpers.get_sectors_from_zone(area[ZONE_CODE_FIELD])
        sectors.sort(key= lambda x: x)

        template = template_env.get_template('templates/templates/area-layout.html')
        output = template.render(
            problems=problems,
            sectors=sectors,
            area_code=area[ZONE_CODE_FIELD],
            name=area[NAME_FIELD],
            file_name=area[ZONE_CODE_FIELD],
            tag_name=area[NAME_FIELD].replace("'", r"\'"),
            guide_list=guides,
            affiliate_guide_list=affiliate_guides,
            map_url='maps/'+area[ZONE_CODE_FIELD],
            area_data=area,
            lat=area[LATITUDE_FIELD],
            lng=area[LONGITUDE_FIELD],
            zone=area[NAME_FIELD])

        with open('templates/zones/'+area[ZONE_CODE_FIELD]+'.html', 'w', encoding='utf-8') as template:
            template.write(output)


if __name__ == '__main__':
    main()
