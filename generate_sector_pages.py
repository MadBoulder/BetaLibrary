import os
from jinja2 import Environment, FileSystemLoader
import utils.helpers
import utils.zone_helpers
import utils.MadBoulderDatabase
from slugify import slugify


def main():
    """
    Generate html templates for all the sectors listed in the processed_data file
    IMPORTANT: the processed_data file should be up to date. It can be extracted from 
    """

    
    dir_path_countries = 'templates/sectors'
    utils.helpers.empty_and_create_dir(dir_path_countries)

    zone_data = utils.MadBoulderDatabase.getAreasData()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone_code, zone in zone_data.items():
        print("generating sectors for: " + zone['name'])
        sectors = utils.zone_helpers.get_sectors_from_zone(zone_code)
        problems_zone = utils.MadBoulderDatabase.getVideoDataFromZone(zone_code)
        playlist = utils.MadBoulderDatabase.getPlaylistdata(zone_code)
        areaInfo = utils.zone_helpers.getStateAndCountryInfo(zone_code)

        for sector in sectors:
            problems = utils.zone_helpers.get_problems_from_sector(problems_zone, sector[1])
            problems.sort(key= lambda x: x['name'])
               
            video_id = ""
            if 'sectors' in playlist:
                for sectorPlaylistCode, sectorPLaylist in playlist['sectors'].items():
                    if slugify(sector[1]) == sectorPlaylistCode:
                        video_id = sectorPLaylist['id']
            template = template_env.get_template(
                'templates/templates/sector_page_template.html')
            output = template.render(
                zone_code=zone_code,
                zone_name=zone['name'],
                sector=sector,
                sector_code=slugify(sector[1]),
                problems=problems,
                video_id=video_id,
                areaInfo=areaInfo
            )
            if not os.path.exists(f'templates/sectors/{zone_code}'):
                os.mkdir(f'templates/sectors/{zone_code}')

            with open(f'templates/sectors/{zone_code}/{slugify(sector[1])}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
