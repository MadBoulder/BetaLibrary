from collections import Counter
import os
from jinja2 import Environment, FileSystemLoader
import utils.zone_helpers
import handle_channel_data
from slugify import slugify


def main():
    """
    Generate html templates for all the countries listed in the countries file
    """

    if not os.path.exists(f'templates/countries'):
        os.mkdir(f'templates/countries')

    if not os.path.exists(f'templates/states'):
        os.mkdir(f'templates/states')

    country_data = handle_channel_data.get_country_data()
    playlists = handle_channel_data.get_playlist_data()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for country in country_data['items']:
        country_code=country['code']
        print("generating country: " + country_code)
        country_name = country.get("name", [""])[0]
        areas = utils.zone_helpers.get_areas_from_country(country['reduced_code'])
        states=country.get("states", [])
        
        area_state_codes = [area.get("state", '') for area in areas]
        state_code_counts = Counter(area_state_codes)

        for state in states:
            if 'count' in state:
                state['count'] += state_code_counts[state['code']]
            else:
                state['count'] = state_code_counts[state['code']]

        template = template_env.get_template(
            'templates/templates/country_layout.html')
        output = template.render(
            country_code=country_code,
            country_name=country_name,
            states=states,
            areas=areas,
            playlists=playlists['items']
        )

        with open(f'templates/countries/{slugify(country_name)}.html', 'w', encoding='utf-8') as template:
            template.write(output)

        for state in states:
            state_code=state['code']
            state_name = state.get("name", [""])[0]
            print("generating state: " + state_code)
            
            state_areas = utils.zone_helpers.get_areas_from_state(state_code)
            state_template = template_env.get_template('templates/templates/state_layout.html')
            state_output = state_template.render(
                country_code=country_code,
                country_name=country_name,
                state_code=state_code,
                state_name=state_name,
                areas=state_areas,
                playlists=playlists['items']
            )

            with open(f'templates/states/{state_code}.html', 'w', encoding='utf-8') as state_template:
                state_template.write(state_output)

if __name__ == '__main__':
    main()
