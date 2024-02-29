from collections import Counter
from jinja2 import Environment, FileSystemLoader
import utils.helpers
from slugify import slugify


def main():
    """
    Generate html templates for all the countries listed in the countries file
    """
    dir_path = 'templates/contributors'
    utils.helpers.empty_and_create_dir(dir_path)

    contributors = utils.helpers.get_contributors_list()

    template_loader = FileSystemLoader(searchpath='.')
    template_env = Environment(loader=template_loader)

    template = template_env.get_template(
        'templates/templates/contributors_list_layout.html')
    output = template.render(
        contributors = contributors
    )

    with open(f'templates/contributors/contributors-list.html', 'w', encoding='utf-8') as template:
        template.write(output)

    for contributor, details in contributors.items():
        contributor_code=contributor
        print("generating contributor page: " + contributor)
        

        template = template_env.get_template(
            'templates/templates/contributor_layout.html')
        output = template.render(
            contributor_code = contributor,
            contributor_name = details['name'],
            problems = details['videos']
        )

        with open(f'templates/contributors/{contributor}.html', 'w', encoding='utf-8') as template:
            template.write(output)

if __name__ == '__main__':
    main()
