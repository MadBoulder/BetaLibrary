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

    areasData = utils.MadBoulderDatabase.getAreasData()
    videoData = utils.MadBoulderDatabase.getAllVideoData()
    countriesData = utils.MadBoulderDatabase.getCountriesData()
    playlistsData = utils.MadBoulderDatabase.getPlaylistsData()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for areaCode, area in areasData.items():
        print("generating sectors for: " + area['name'])
        if areaCode in videoData:
            problems_zone = videoData[areaCode]
        sectors = utils.zone_helpers.getSectors(problems_zone)
        if areaCode in playlistsData:
            playlist = playlistsData[areaCode]
        areaInfo = utils.zone_helpers.getStateAndCountryInfoFromData(areasData, countriesData, areaCode)


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
                zone_code=areaCode,
                zone_name=area['name'],
                sector=sector,
                sector_code=slugify(sector[1]),
                problems=problems,
                video_id=video_id,
                areaInfo=areaInfo
            )
            if not os.path.exists(f'templates/sectors/{areaCode}'):
                os.mkdir(f'templates/sectors/{areaCode}')

            with open(f'templates/sectors/{areaCode}/{slugify(sector[1])}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
