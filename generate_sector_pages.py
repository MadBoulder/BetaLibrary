import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers


def get_embed_url(full_url):
    return f'https://www.youtube.com/embed/{full_url.split("/")[-1].replace("watch?v=", "")}'

def main():
    """
    Generate html templates for all the sectors listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """
    zones = next(os.walk('data/zones/'))[1]

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone_code in zones:
        sectors = utils.zone_helpers.get_sectors_from_zone(zone_code)
        problems_zone = utils.zone_helpers.get_problems_from_zone(zone_code)

        for sector in sectors:
            problems = utils.zone_helpers.get_problems_from_sector(problems_zone, sector[1])
            problems.sort(key= lambda x: x['name'])
            video_url = utils.zone_helpers.get_playlist_url_from_sector(zone_code, sector);
            template = template_env.get_template(
                'templates/sector_layout.html')
            output = template.render(
                sector=sector,
                problems=problems,
                video_url=video_url,
                layout_css='../../../static/css/layout.css'
            )
            if not os.path.exists(f'templates/sectors/{zone_code}'):
                os.mkdir(f'templates/sectors/{zone_code}')

            with open(f'templates/sectors/{zone_code}/{sector[1]}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
