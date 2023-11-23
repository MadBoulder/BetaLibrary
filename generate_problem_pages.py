import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
import handle_channel_data
from slugify import slugify

LINK_FIELD = 'url'
CLIMBER_FIELD = 'climber'
NAME_FIELD = 'name'
GRADE_FIELD = 'grade'
GRADE_WITH_INFO_FIELD = 'grade_with_info'
ZONE_FIELD = 'zone'
SSECTOR_FIELD = 'sector'

def get_embed_url(full_url):
    return f'https://www.youtube.com/embed/{full_url.split("/")[-1].replace("watch?v=", "")}'

def main():
    """
    Generate html templates for all the problems listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """
    zone_data = handle_channel_data.get_zone_data()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone in zone_data['items']:
        zone_code = zone['zone_code']
        problems = utils.zone_helpers.get_problems_from_zone_code(zone_code)

        #country
        country = utils.zone_helpers.get_country_from_code(zone['country'])
        country_name = country.get('name','')[0] if country else ''

        state = utils.zone_helpers.get_state_from_code(zone.get('state',''))
        state_code = state.get('code','') if state else ''
        state_name = state.get('name','')[0] if state else ''

        for problem in problems:
            template = template_env.get_template(
                'templates/templates/problem-layout.html')
            output = template.render(
                climber=problem[CLIMBER_FIELD],
                name=problem[NAME_FIELD],
                name_code=slugify(problem[NAME_FIELD]),
                grade=problem[GRADE_WITH_INFO_FIELD],
                zone=problem[ZONE_FIELD],
                zone_code=zone_code,
                sector=problem[SSECTOR_FIELD],
                sector_code=slugify(problem[SSECTOR_FIELD]),
                video_url=get_embed_url(problem[LINK_FIELD]),
                country_code=country.get('code',''),
                country_name=country_name,
                state_code=state_code,
                state_name=state_name
            )
            if not os.path.exists(f'templates/problems/{zone_code}'):
                os.mkdir(f'templates/problems/{zone_code}')

            with open(f'templates/problems/{zone_code}/{slugify(problem["name"])}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
