import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
import handle_channel_data
from slugify import slugify


def main():
    """
    Generate html templates for all the sectors listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """

    if not os.path.exists(f'templates/sectors'):
        os.mkdir(f'templates/sectors')

    zone_data = handle_channel_data.get_zone_data()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone in zone_data['items']:
        print("generating zone: " + zone['name'])
        zone_code = zone['zone_code']  
        sectors = utils.zone_helpers.get_sectors_from_zone(zone_code)
        problems_zone = utils.zone_helpers.get_problems_from_zone_code(zone_code)

        for sector in sectors:
            problems = utils.zone_helpers.get_problems_from_sector(problems_zone, sector[1])
            problems.sort(key= lambda x: x['name'])
            for p in problems:
                p['secure'] = slugify(p['name'])
            video_url = ""
            if 'sectors' in zone:
                for s in zone['sectors']:
                    if sector[1] == slugify(s['name']):
                        video_url = s['url']
            template = template_env.get_template(
                'templates/templates/sector-layout.html')
            output = template.render(
                zone_code=zone_code,
                zone_name=zone['name'],
                sector=sector,
                sector_code=slugify(sector[1]),
                problems=problems,
                video_url=video_url
            )
            if not os.path.exists(f'templates/sectors/{zone_code}'):
                os.mkdir(f'templates/sectors/{zone_code}')

            with open(f'templates/sectors/{zone_code}/{slugify(sector[1])}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
