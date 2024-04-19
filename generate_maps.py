import load_map
import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.js_helpers
from utils.id_generator import IDGenerator
import utils.MadBoulderDatabase

ZONES_PATH = 'data/zones/'


def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    generate_ids = IDGenerator()
    areas = utils.MadBoulderDatabase.getAreasData()
    for araCode, area in areas.items():
        print(araCode)
        with open('templates/maps/'+araCode+'.html', 'w', encoding='utf-8') as template:
            template.write(
                load_map.load_map(
                    araCode,
                    ZONES_PATH + araCode + '/' + araCode + '.json',
                    generate_ids,
                    True
                )
            )

    with open('templates/maps/world.html', 'w', encoding='utf-8') as template:
        template.write(
            load_map.load_general_map(
                areas,
                generate_ids,
                True
            )
        )


if __name__ == '__main__':
    main()
