import load_map
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
import helpers


def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    areas = next(os.walk('data/zones/'))[1]
    all_data = ['data/zones/' + area + '/' + area + '.txt' for area in areas]
    for area in areas:
        print(area)
        with open('templates/maps/'+area+'.html', 'w', encoding='utf-8') as template:
            template.write(load_map.load_map(
                'data/zones/' + area + '/' + area + '.txt', True))

    with open('templates/maps/all_to_render.html', 'w', encoding='utf-8') as template:
        template.write(load_map.load_general_map(
            all_data, True))

    # When generating templates update also the all template
    template_loader = FileSystemLoader(searchpath=".")
    template_env = Environment(loader=template_loader)
    data = helpers.get_number_of_videos_from_playlists_file(
        'data/playlist.txt')
    template = template_env.get_template('templates/maps/all_to_render.html')
    # Here we replace zone_name in maps/all by the number of beta videos
    output = template.render(**data)
    with open('templates/maps/all.html', 'w', encoding="utf-8") as template:
        template.write(output)


if __name__ == '__main__':
    main()
