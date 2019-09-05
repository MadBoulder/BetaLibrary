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
        print(area)
        with open('templates/maps/'+area+'.html', 'wb') as template:
            template.write(load_map.load_map(
                'data/zones/' + area + '/' + area + '.txt', True).encode('utf-8'))

    with open('templates/maps/all.html', 'wb') as template:
        template.write(load_map.load_general_map(all_data, True).encode('utf-8'))


if __name__ == '__main__':
    main()
