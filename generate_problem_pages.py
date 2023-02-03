import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
from werkzeug.utils import secure_filename

LINK_FIELD = 'url'
NAME_FIELD = 'name'
GRADE_FIELD = 'grade'


def main():
    """
    Generate html templates for all the problems listed in the processed_data file
    """
    zones = next(os.walk('data/zones/'))[1]

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone_code in zones:
        problems = utils.zone_helpers.get_problems_from_zone(zone_code)

        for problem in problems:
            template = template_env.get_template(
                'templates/problem_layout.html')
            # eventually get sector also?
            output = template.render(
                name=problem[NAME_FIELD],
                grade=problem[GRADE_FIELD],
                video_url=problem[LINK_FIELD],
                layout_css='static/css/layout.css'
            )
            if not os.path.exists(f'templates/problems/{zone_code}'):
                os.mkdir(f'templates/problems/{zone_code}')

            with open(f'templates/problems/{zone_code}/{secure_filename(problem["name"])}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
