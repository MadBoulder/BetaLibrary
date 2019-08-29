import load_map
import os


def main():
    """
    Generate html map templates for all the areas located inside the data folder
    as well as a general map that contains all the areas
    """
    areas = next(os.walk('data/zones/'))[1]
    all_data = ['data/zones/' + area + '/' + area + '.txt' for area in areas]
    for area in areas:
        with open('templates/maps/'+area+'.html', 'w') as template:
            template.write(load_map.load_map(
                'data/zones/' + area + '/' + area + '.txt', True))

    with open('templates/maps/all.html', 'w') as template:
        template.write(load_map.load_general_map(all_data, True))


if __name__ == '__main__':
    main()
