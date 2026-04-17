from collections import Counter
from jinja2 import Environment, FileSystemLoader
import utils.zone_helpers
import utils.helpers
import handle_channel_data
from slugify import slugify


def main():
    dir_path_countries = 'templates/countries'
    utils.helpers.empty_and_create_dir(dir_path_countries)
    dir_path_countries_es = 'templates/countries/es'
    utils.helpers.empty_and_create_dir(dir_path_countries_es)
    dir_path_states = 'templates/states'
    utils.helpers.empty_and_create_dir(dir_path_states)
    dir_path_states_es = 'templates/states/es'
    utils.helpers.empty_and_create_dir(dir_path_states_es)

    country_data = utils.MadBoulderDatabase.getCountriesData()
    playlists = utils.MadBoulderDatabase.getPlaylistsData()
    areasData = utils.MadBoulderDatabase.getAreasData()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    for country_code, country in country_data.items():
        print("generating country: " + country_code)
        country_name = country.get("name", [""])[0]
        areas = utils.zone_helpers.get_areas_from_country(country_code, areasData)
        states=country.get("states", {})
        overview=country['overview'][0]
        
        area_state_codes = [area.get("state", '') for area in areas.values()]
        state_code_counts = Counter(area_state_codes)

        for state_code, state in states.items():
            if 'count' in state:
                state['count'] += state_code_counts[state_code]
            else:
                state['count'] = state_code_counts[state_code]

        template = template_env.get_template(
            'templates/templates/country_page_template.html')
        output = template.render(
            country_code=country_code,
            country_name=country_name,
            states=states,
            areas=areas,
            playlists=playlists,
            overview=overview
        )

        with open(f'templates/countries/{slugify(country_name)}.html', 'w', encoding='utf-8') as template:
            template.write(output)

        country_name_es = country.get("name", [""])[1]
        overview_es=country['overview'][1]
        template = template_env.get_template(
            'templates/templates/es/country_page_template.html')
        output = template.render(
            country_code=country_code,
            country_name=country_name_es,
            states=states,
            areas=areas,
            playlists=playlists,
            overview=overview_es
        )

        with open(f'templates/countries/es/{slugify(country_name)}.html', 'w', encoding='utf-8') as template:
            template.write(output)

        for state_code, state in states.items():
            state_name = state.get("name", [""])[0]
            state_name_es = state.get("name", ["", ""])[1] if len(state.get("name", [])) > 1 else state_name
            state_overview = state.get("overview", ["", ""])
            state_overview_en = state_overview[0] if len(state_overview) > 0 else ""
            state_overview_es = state_overview[1] if len(state_overview) > 1 else ""
            print("generating state: " + state_code)

            state_areas = utils.zone_helpers.get_areas_from_state(state_code, areasData)
            state_template = template_env.get_template('templates/templates/state_page_template.html')
            state_output = state_template.render(
                country_code=country_code,
                country_name=country_name,
                state_code=state_code,
                state_name=state_name,
                areas=state_areas,
                playlists=playlists,
                overview=state_overview_en
            )

            with open(f'templates/states/{state_code}.html', 'w', encoding='utf-8') as state_template_file:
                state_template_file.write(state_output)

            state_template_es = template_env.get_template('templates/templates/es/state_page_template.html')
            state_output_es = state_template_es.render(
                country_code=country_code,
                country_name=country_name_es,
                state_code=state_code,
                state_name=state_name_es,
                areas=state_areas,
                playlists=playlists,
                overview=state_overview_es
            )

            with open(f'templates/states/es/{state_code}.html', 'w', encoding='utf-8') as state_template_es_file:
                state_template_es_file.write(state_output_es)

if __name__ == '__main__':
    main()
