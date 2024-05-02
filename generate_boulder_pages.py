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


def extract_location_info(zone_data, key):
    """
    Helper function to extract country or state code and name from zone data.
    """
    location = zone_data.get(key, {})
    code = location.get('code', '')
    name = location.get('name', '')
    return code, name[0] if isinstance(name, list) else name


def main():
    """
    Generate html templates for all the problems listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """
    areasData = utils.MadBoulderDatabase.getAreasData()
    countriesData = utils.MadBoulderDatabase.getCountriesData()
    all_areas_with_boulders = utils.MadBoulderDatabase.getAllBoulderData()
    videoData = utils.MadBoulderDatabase.getAllVideoData()

    dir_path_countries = 'templates/boulders'
    utils.helpers.empty_and_create_dir(dir_path_countries)

    template_env = Environment(loader=FileSystemLoader(searchpath='.'))

    for area_code, boulders in all_areas_with_boulders.items():
        print("Generating Boulder Pages for " + area_code)

        if area_code in videoData:
            problems = videoData[area_code]
        areaInfo = utils.zone_helpers.getStateAndCountryInfoFromData(areasData, countriesData, area_code)


        for boulder_code, boulder in boulders.items():
            boulder_problems = [problem for problem in problems.values() if problem.get('boulder_code') == boulder_code]
            if not boulder_problems:
                continue

            template = template_env.get_template(
                'templates/templates/boulder_template.html')
            output_path = os.path.join(dir_path_countries, area_code, f"{boulder_code}.html")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            output = template.render(
                problems = boulder_problems,
                name=boulder['name'],
                boulder_code=boulder_code,
                zone=boulder_problems[0][ZONE_FIELD],
                zone_code=area_code,
                sector=boulder_problems[0][SECTOR_FIELD],
                sector_code=boulder_problems[0][SECTOR_CODE_FIELD],
                areaInfo=areaInfo,
                coordinates=boulder['coordinates']
            )

            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(output)


if __name__ == '__main__':
    main()
