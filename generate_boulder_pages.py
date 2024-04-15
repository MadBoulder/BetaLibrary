import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
import utils.MadBoulderDatabase
from slugify import slugify

NAME_FIELD = 'name'
ZONE_FIELD = 'zone'
ZONE_CODE_FIELD = 'zone_code'
SECTOR_FIELD = 'sector'
SECTOR_CODE_FIELD = 'sector_code'
BOULDER_FIELD = 'boulder'
BOULDER_CODE_FIELD = 'boulder_code'

def main():
    """
    Generate html templates for all the problems listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """
    zones_data = utils.MadBoulderDatabase.get_zone_data()
    all_areas_list = utils.helpers.get_all_areas_list()
    
    all_areas_with_boulders = utils.MadBoulderDatabase.get_boulder_data()

    dir_path_countries = 'templates/boulders'
    utils.helpers.empty_and_create_dir(dir_path_countries)

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for area_with_boulders in all_areas_with_boulders:
        zone_code = area_with_boulders['area_code']
        print("Generating Boulder Pages for " + zone_code)
        zone_data = utils.helpers.find_item(zones_data, "zone_code", zone_code)
        zone_added = zone_data is not None

        problems = utils.MadBoulderDatabase.getVideoDataFromZone(zone_code)

        boulders = next((item['boulders'] for item in all_areas_with_boulders if item['area_code'] == zone_code), None)
        if boulders:
            for boulder in boulders:
                boulder_code = boulder.get('name_code')
                boulder['problems'] = [problem for problem in problems if problem.get('boulder_code') == boulder_code]
                if boulder['problems']:
                    #country
                    country_name = ''
                    country_code = ''
                    if zone_data:
                        country = utils.zone_helpers.get_country_from_code(zone_data.get('country',''))
                        country_code = country.get('code','') if country else ''
                        country_name = country.get('name','')[0] if country else ''

                    state_name = ''
                    state_code = ''
                    if zone_data:
                        state = utils.zone_helpers.get_state_from_code(zone_data.get('state',''))
                        state_code = state.get('code','') if state else ''
                        state_name = state.get('name','')[0] if state else ''

                    template = template_env.get_template(
                        'templates/templates/boulder_template.html')
                    output = template.render(
                        problems = boulder['problems'],
                        name=boulder['name'],
                        boulder_code=boulder_code,
                        zone=boulder['problems'][0][ZONE_FIELD],
                        zone_code=zone_code,
                        sector=boulder['problems'][0][SECTOR_FIELD],
                        sector_code=boulder['problems'][0][SECTOR_CODE_FIELD],
                        country_code=country_code,
                        country_name=country_name,
                        state_code=state_code,
                        state_name=state_name,
                        zone_added=zone_added,
                        coordinates=boulder['coordinates']
                    )
                    if not os.path.exists(f'templates/boulders/{zone_code}'):
                        os.mkdir(f'templates/boulders/{zone_code}')

                    with open(f'templates/boulders/{zone_code}/{boulder_code}.html', 'w', encoding='utf-8') as template:
                        template.write(output)


if __name__ == '__main__':
    main()
