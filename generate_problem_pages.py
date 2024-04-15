import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
import handle_channel_data
import utils.database
from slugify import slugify

CLIMBER_FIELD = 'climber'
CLIMBER_CODE_FIELD = 'climber_code'
TITLE_FIELD = 'title'
NAME_FIELD = 'name'
GRADE_FIELD = 'grade'
GRADE_WITH_INFO_FIELD = 'grade_with_info'
ZONE_FIELD = 'zone'
ZONE_CODE_FIELD = 'zone_code'
SECTOR_FIELD = 'sector'
SECTOR_CODE_FIELD = 'sector_code'
BOULDER_FIELD = 'boulder'
BOULDER_CODE_FIELD = 'boulder_code'



def get_embed_url(videoId):
    return f'https://www.youtube.com/embed/{videoId}'

def main():
    """
    Generate html templates for all the problems listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """
    zones_data = handle_channel_data.get_zone_data()
    all_areas_list = utils.helpers.get_all_areas_list()
    
    boulders = {area['area_code']: {boulder['name_code']: boulder['coordinates'] for boulder in area['boulders']} for area in handle_channel_data.get_boulder_data()}

    dir_path_countries = 'templates/problems'
    utils.helpers.empty_and_create_dir(dir_path_countries)

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone_code in all_areas_list:
        print("Generating Problems for " + zone_code)
        zone_data = utils.helpers.find_item(zones_data, "zone_code", zone_code)
        zone_added = zone_data is not None

        problems = utils.database.getVideoDataFromZone(zone_code)

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

        for problem in problems:
            coordinates = None
            boulder_code = ''
            if zone_code in boulders:
                boulder_code = problem.get(BOULDER_CODE_FIELD)
                if boulder_code and boulder_code in boulders[zone_code]:
                    coordinates = boulders[zone_code][boulder_code]
            
            boulder_name = problem.get(BOULDER_FIELD, '')

            file_name = problem['secure_slug']
            template = template_env.get_template(
                'templates/templates/problem_template.html')
            output = template.render(
                climber=problem[CLIMBER_FIELD],
                climber_code=problem[CLIMBER_CODE_FIELD],
                name=problem[NAME_FIELD],
                title=problem[TITLE_FIELD],
                grade=problem[GRADE_WITH_INFO_FIELD],
                zone=problem[ZONE_FIELD],
                zone_code=zone_code,
                sector=problem[SECTOR_FIELD],
                sector_code=problem[SECTOR_CODE_FIELD],
                video_url=get_embed_url(problem['id']),
                country_code=country_code,
                country_name=country_name,
                state_code=state_code,
                state_name=state_name,
                file_name=file_name,
                zone_added=zone_added,
                coordinates=coordinates,
                boulder_code=boulder_code,
                boulder_name=boulder_name
            )
            if not os.path.exists(f'templates/problems/{zone_code}'):
                os.mkdir(f'templates/problems/{zone_code}')

            with open(f'templates/problems/{file_name}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
