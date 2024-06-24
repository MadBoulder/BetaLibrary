import load_map
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
    for areaCode, areaData in areas.items():
        print(areaCode)
        with open('templates/maps/'+areaCode+'.html', 'w', encoding='utf-8') as template:
            template.write(
                load_map.load_map(
                    areaCode,
                    areaData,
                    ZONES_PATH + areaCode + '/' + areaCode + '.json',
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
