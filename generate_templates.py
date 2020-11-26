import load_map
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
import helpers
import utils.js_helpers
from utils.id_generator import IDGenerator

ZONES_PATH = 'data/zones/'

def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    generate_ids = IDGenerator()
    areas = next(os.walk(ZONES_PATH))[1]
    all_data = [ZONES_PATH + area + '/' + area + '.txt' for area in areas]
    for area in areas:
        print(area)
        with open('templates/maps/'+area+'.html', 'w', encoding='utf-8') as template:
            template.write(
                load_map.load_map(
                    area,
                    ZONES_PATH + area + '/' + area + '.txt',
                    generate_ids,
                    True
                )
            )

    with open('templates/maps/all_to_render.html', 'w', encoding='utf-8') as template:
        template.write(
            load_map.load_general_map(
                all_data,
                generate_ids,
                True
            )
        )

    # When generating templates update also the all template
    template_loader = FileSystemLoader(searchpath=".")
    template_env = Environment(loader=template_loader)
    data = helpers.get_number_of_videos_from_playlists_file(
        'data/playlist.txt')
    template = template_env.get_template('templates/maps/all_to_render.html')
    # Here we replace zone_name in maps/all by the number of beta videos
    output = template.render(**data)
    output = utils.js_helpers.replace_sectors_placeholders_for_translations(
        output)
    with open('templates/maps/all.html', 'w', encoding="utf-8") as template:
        template.write(output)


if __name__ == '__main__':
    main()
