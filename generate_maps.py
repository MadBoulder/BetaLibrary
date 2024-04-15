import load_map
import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.js_helpers
from utils.id_generator import IDGenerator
import handle_channel_data

ZONES_PATH = 'data/zones/'


def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    generate_ids = IDGenerator()
    zone_data = handle_channel_data.get_zone_data()
    for zone in zone_data:
        print(zone['zone_code'])
        with open('templates/maps/'+zone['zone_code']+'.html', 'w', encoding='utf-8') as template:
            template.write(
                load_map.load_map(
                    zone['zone_code'],
                    ZONES_PATH + zone['zone_code'] + '/' + zone['zone_code'] + '.json',
                    generate_ids,
                    True
                )
            )

    with open('templates/maps/world.html', 'w', encoding='utf-8') as template:
        template.write(
            load_map.load_general_map(
                zone_data,
                generate_ids,
                True
            )
        )


if __name__ == '__main__':
    main()
