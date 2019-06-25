import numpy as np
import folium
from folium.plugins import MarkerCluster, BeautifyIcon
import json
import os
import helpers

POPUP_WIDTH = 100

### GENERATE MAP ###

def load_map(datafile, return_html=True):
    """
    Create an area map with boulder markers and video links from a JSON file
    """
    area_data = {}
    with open(datafile) as data:
        area_data = json.load(data)

    area_map = folium.Map(location=[area_data['latitude'], area_data['longitude']],
        zoom_start=area_data['zoom'])

    sectors = area_data['sectors']
    #Create a Folium feature group for this layer, since we will be displaying multiple layers
    sector_lyr = folium.FeatureGroup(name='sectors_layer')
    for sector in sectors:
        sector_map = folium.GeoJson(
            os.path.dirname(os.path.abspath(datafile))+sector['sector_data'],
            name=sector['name'],
            tooltip=sector['name'],
            style_function=lambda x: {
                'color' : x['properties']['stroke'],
                'weight' : x['properties']['stroke-width'],
                'opacity': 0.6,
                'fillColor' : x['properties']['stroke'],
            }
        )
        sector_html = helpers.generate_sector_html(sector['name'], sector['link'])
        sector_map.add_child(folium.Popup(sector_html, max_width=POPUP_WIDTH, min_width=POPUP_WIDTH))

        sector_lyr.add_child(sector_map)

    # Parking
    for parking in area_data['parkings']:
        parking_marker = folium.Marker(
            location=[parking['parking_latitude'], parking['parking_longitude']],
            popup='Parking',
            tooltip='Parking',
            icon=folium.Icon(color='red', icon='info-sign')
        )

        sector_lyr.add_child(parking_marker)

    # Sectors
    zoomed_out_lyr = folium.FeatureGroup(name='zoomed_out_layer')
    zoomed_out_icon = BeautifyIcon(icon_shape='marker',
        number=len(area_data['sectors'])
        )

    sectors_marker = folium.Marker(
        location=[area_data['latitude'],area_data['longitude']],
        tooltip='Sectors',
        icon=zoomed_out_icon
    )

    zoomed_out_lyr.add_child(sectors_marker)

    area_map.add_child(zoomed_out_lyr)
    area_map.add_child(sector_lyr)

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting JavaScript code in the map html
    map_html = area_map.get_root().render()
    map_html = helpers.make_layer_that_hides(map_html, area_map.get_name(), sector_lyr.get_name(), 15)
    map_html = helpers.make_layer_that_hides(map_html, area_map.get_name(), zoomed_out_lyr.get_name(), 15, False, True)

    return map_html if return_html else area_map


def load_general_map(datafiles, return_html=True):
    """
    Create a map that contains all the bouldering areas.
    """
    area_map = folium.Map(location=[-33.046875, 66.51326044311185],
        zoom_start=2)

    layers = []

    for areadatafile in datafiles:
        area_data = {}
        with open(areadatafile) as data:
            area_data = json.load(data)

        sectors = area_data['sectors']
        # Create a Folium feature group for this layer, since we will be displaying multiple layers
        sector_lyr = folium.FeatureGroup(name='sectors_layer')
        for sector in sectors:
            sector_map = folium.GeoJson(
                os.path.dirname(os.path.abspath(areadatafile))+sector['sector_data'],
                name=sector['name'],
                tooltip=sector['name'],
                style_function=lambda x: {
                    'color' : x['properties']['stroke'],
                    'weight' : x['properties']['stroke-width'],
                    'opacity': 0.6,
                    'fillColor' : x['properties']['stroke'],
                }
            )
            sector_html = helpers.generate_sector_html(sector['name'], sector['link'])
            sector_map.add_child(folium.Popup(sector_html, max_width=POPUP_WIDTH, min_width=POPUP_WIDTH))

            sector_lyr.add_child(sector_map)

        # Parking
        for parking in area_data['parkings']:
            parking_marker = folium.Marker(
                location=[parking['parking_latitude'], parking['parking_longitude']],
                popup='Parking',
                tooltip='Parking',
                icon=folium.Icon(color='red', icon='info-sign')
            )

            sector_lyr.add_child(parking_marker)

        # Sectors
        zoomed_out_lyr = folium.FeatureGroup(name='zoomed_out_layer')
        zoomed_out_icon = BeautifyIcon(icon_shape='marker',
            number=len(area_data['sectors'])
            )

        sectors_marker = folium.Marker(
            location=[area_data['latitude'],area_data['longitude']],
            tooltip='Sectors',
            icon=zoomed_out_icon
        )

        zoomed_out_lyr.add_child(sectors_marker)

        area_map.add_child(zoomed_out_lyr)
        area_map.add_child(sector_lyr)
        layers += [(sector_lyr, zoomed_out_lyr)]

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting JavaScript code in the map html
    map_html = area_map.get_root().render()
    for sector_lyr, zoomed_out_lyr in layers:
        map_html = helpers.make_layer_that_hides(map_html, area_map.get_name(), sector_lyr.get_name(), 14, False, False)
        map_html = helpers.make_layer_that_hides(map_html, area_map.get_name(), zoomed_out_lyr.get_name(), 14, True, True)

    return map_html if return_html else area_map
