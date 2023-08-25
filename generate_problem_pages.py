import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
from werkzeug.utils import secure_filename

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
    zones = next(os.walk('data/zones/'))[1]

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone_code in zones:
        problems = utils.zone_helpers.get_problems_from_zone(zone_code)

        for problem in problems:
            template = template_env.get_template(
                'templates/problem_layout.html')
            output = template.render(
                climber=problem[CLIMBER_FIELD],
                name=problem[NAME_FIELD],
                grade=problem[GRADE_WITH_INFO_FIELD],
                zone=problem[ZONE_FIELD],
                sector=problem[SSECTOR_FIELD],
                video_url=get_embed_url(problem[LINK_FIELD])
            )
            if not os.path.exists(f'templates/problems/{zone_code}'):
                os.mkdir(f'templates/problems/{zone_code}')

            with open(f'templates/problems/{zone_code}/{secure_filename(problem["name"])}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
