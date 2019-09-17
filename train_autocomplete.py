import autocomplete
from autocomplete import models
import os
import json


def main():
    """
    """
    areas = next(os.walk('data/zones/'))[1]
    zones = []
    for area in areas:
        datafile = 'data/zones/' + area + '/' + area + '.txt'
        area_data = {}
        with open(datafile) as data:
            area_data = json.load(data)
        zones += [area_data['name']]
    names = " a ".join(zones)
    names = "a " + names
    models.train_models(names)
    models.save_models(path='search_data.pkl')
    print("Model trained")


if __name__ == "__main__":
    main()
