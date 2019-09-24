import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json


def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    areas = next(os.walk('data/zones/'))[1]
    all_data = ['data/zones/' + area + '/' + area + '.txt' for area in areas]

    template_loader = FileSystemLoader(searchpath=".")
    template_env = Environment(loader=template_loader)

    playlists = {}
    for area in areas:
        # Create zone map
        print(area)
        datafile = 'data/zones/' + area + '/' + area + '.txt'
        area_data = {}
        with open(datafile) as data:
            area_data = json.load(data)

        guides = [(guide['name'], guide['link'])
                  for guide in area_data['guides']]

        base_url = "https://www.youtube.com/embed/?listType=playlist&list="
        playlists[area] = area_data['playlist']
        sectors_playlists = [(sector['name'], base_url + sector['link'].split("list=")[1])
                             for sector in area_data['sectors'] if sector['link']]

        template = template_env.get_template('templates/zone_layout.html')
        output = template.render(
            name=area_data['name'], guide_list=guides,
            map_url='maps/'+area, full_playlist=base_url + area_data['playlist'],
            playlists=sectors_playlists)
        with open('templates/zones/'+area+'.html', 'w') as template:
            template.write(output)

    # Update playlists file
    with open('data/playlist.txt', 'w') as playlists_file:
        playlists_file.write(json.dumps(playlists))


if __name__ == '__main__':
    main()
