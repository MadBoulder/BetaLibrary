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
        # Create zone map
        print(area)
        datafile = 'data/zones/' + area + '/' + area + '.txt'
        area_data = {}
        with open(datafile) as data:
            area_data = json.load(data)
        zones += [area_data['name']]
    names = " ".join(zones)
    models.train_models(names)
    print(names)
    print(autocomplete.predict('Bagni', 'd'))

if __name__ == "__main__":
    main()
