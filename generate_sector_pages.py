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

    
    dir_path_countries = 'templates/sectors'
    utils.helpers.empty_and_create_dir(dir_path_countries)

    zone_data = handle_channel_data.get_zone_data()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for zone in zone_data['items']:
        print("generating zone: " + zone['name'])
        zone_code = zone['zone_code']  
        sectors = utils.zone_helpers.get_sectors_from_zone(zone_code)
        problems_zone = utils.zone_helpers.get_problems_from_zone_code(zone_code)
        playlists = utils.zone_helpers.get_playlists_from_zone(zone_code)
        
        #country
        country = utils.zone_helpers.get_country_from_code(zone['country'])
        country_name = country.get('name','')[0] if country else ''

        state = utils.zone_helpers.get_state_from_code(zone.get('state',''))
        state_code = state.get('code','') if state else ''
        state_name = state.get('name','')[0] if state else ''

        for sector in sectors:
            problems = utils.zone_helpers.get_problems_from_sector(problems_zone, sector[1])
            problems.sort(key= lambda x: x['name'])
            for p in problems:
                p['secure'] = slugify(p['name']) + '-'+ slugify(p['grade_with_info'])
               
            video_id = ""
            if 'sectors' in playlists:
                for s in playlists['sectors']:
                    if slugify(sector[1]) == s['sector_code']:
                        video_id = s['id']
            template = template_env.get_template(
                'templates/templates/sector_page_template.html')
            output = template.render(
                zone_code=zone_code,
                zone_name=zone['name'],
                sector=sector,
                sector_code=slugify(sector[1]),
                problems=problems,
                video_id=video_id,
                country_code=country.get('code',''),
                country_name=country_name,
                state_code=state_code,
                state_name=state_name
            )
            if not os.path.exists(f'templates/sectors/{zone_code}'):
                os.mkdir(f'templates/sectors/{zone_code}')

            with open(f'templates/sectors/{zone_code}/{slugify(sector[1])}.html', 'w', encoding='utf-8') as template:
                template.write(output)


if __name__ == '__main__':
    main()
