import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
import utils.MadBoulderDatabase
import utils.channel
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


def main():
    """
    Generate html templates for all the problems listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """
    videoData = utils.MadBoulderDatabase.getAllVideoData()
    boulderData = utils.MadBoulderDatabase.getAllBoulderData()
    areasData = utils.MadBoulderDatabase.getAreasData()
    countriesData = utils.MadBoulderDatabase.getCountriesData()
    
    dir_path_countries = 'templates/problems'
    utils.helpers.empty_and_create_dir(dir_path_countries)

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone_code, problems in videoData.items():
        print(f"Generating Problems for {zone_code}")

        areaInfo = utils.zone_helpers.getStateAndCountryInfoFromData(areasData, countriesData, zone_code)

        for problem in problems.values():
            coordinates = None
            boulder_code = ''
            if zone_code in boulderData:
                boulder_code = problem.get(BOULDER_CODE_FIELD)
                if boulder_code and boulder_code in boulderData[zone_code]:
                    coordinates = boulderData[zone_code][boulder_code]['coordinates']
            
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
                video_url=utils.channel.getEmbedUrl(problem['id']),
                areaInfo=areaInfo,
                file_name=file_name,
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
