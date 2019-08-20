import numpy as np
import folium
from folium.plugins import MarkerCluster, BeautifyIcon
import json
import os
import helpers

POPUP_WIDTH = 100
DEFAULT_AREA_ZOOM = 14
SECTOR_OPACITY = 0.6

### GENERATE MAP ###


def load_map(datafile, return_html=True):
    """
    Create a map for a bouldering area that shows the GEOJSON data, names and 
    links to video playlists of its sectors as well as the parking areas. All 
    this data should be provided via a JSON file
    """
    area_data = {}
    with open(datafile) as data:
        area_data = json.load(data)

    area_map = folium.Map(location=[area_data['latitude'], area_data['longitude']],
                          zoom_start=area_data['zoom'])

    sectors = area_data['sectors']
    # Create a Folium feature group for this layer, since we will be displaying multiple layers
    sector_lyr = folium.FeatureGroup(name='sectors_layer')
    for sector in sectors:
        sector_map = folium.GeoJson(
            os.path.dirname(os.path.abspath(datafile))+sector['sector_data'],
            name=sector['name'],
            tooltip=sector['name'],
            style_function=lambda x: {
                'color': x['properties']['stroke'],
                'weight': x['properties']['stroke-width'],
                'opacity': SECTOR_OPACITY,
                'fillColor': x['properties']['stroke'],
            }
        )
        sector_html = helpers.generate_sector_html(
            sector['name'], sector['link'])
        sector_map.add_child(folium.Popup(
            sector_html, max_width=POPUP_WIDTH, min_width=POPUP_WIDTH))

        sector_lyr.add_child(sector_map)

    # Parking areas
    for parking in area_data['parkings']:
        parking_marker = folium.Marker(
            location=[parking['parking_latitude'],
                      parking['parking_longitude']],
            popup=helpers.generate_parking_html([parking['parking_latitude'],
                                                 parking['parking_longitude']]),
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
        location=[area_data['latitude'], area_data['longitude']],
        tooltip=area_data['name'],
        icon=zoomed_out_icon
    )

    zoomed_out_lyr.add_child(sectors_marker)

    area_map.add_child(zoomed_out_lyr)
    area_map.add_child(sector_lyr)

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting JavaScript code in the map html
    map_html = area_map.get_root().render()
    map_html = helpers.make_layer_that_hides(
        map_html, area_map.get_name(), sector_lyr.get_name(), DEFAULT_AREA_ZOOM)
    map_html = helpers.make_layer_that_hides(
        map_html, area_map.get_name(), zoomed_out_lyr.get_name(), DEFAULT_AREA_ZOOM, False, True)
    # Zoom into area when clicking
    map_html = helpers.zoom_on_click(
        map_html, area_map.get_name(), sectors_marker.get_name(), DEFAULT_AREA_ZOOM+1)

    return map_html if return_html else area_map


def load_general_map(datafiles, return_html=True):
    """
    Create a map that contains all the info provided by the list of datafiles
    i.e. all areas combined
    """
    area_map = folium.Map(location=[-33.046875, 66.51326044311185],
                          zoom_start=2)

    layers = []
    sectors_markers = []

    # Sectors layer
    zoomed_out_lyr = folium.FeatureGroup(name='zoomed_out_layer')
    areas_cluster = MarkerCluster()

    for areadatafile in datafiles:
        area_data = {}
        with open(areadatafile) as data:
            area_data = json.load(data)

        sectors = area_data['sectors']
        # Create a Folium feature group for this layer, since we will be displaying multiple layers
        sector_lyr = folium.FeatureGroup(name='sectors_layer')
        for sector in sectors:
            sector_map = folium.GeoJson(
                os.path.dirname(os.path.abspath(areadatafile)) +
                sector['sector_data'],
                name=sector['name'],
                tooltip=sector['name'],
                style_function=lambda x: {
                    'color': x['properties']['stroke'],
                    'weight': x['properties']['stroke-width'],
                    'opacity': SECTOR_OPACITY,
                    'fillColor': x['properties']['stroke'],
                }
            )
            sector_html = helpers.generate_sector_html(
                sector['name'], sector['link'])
            sector_map.add_child(folium.Popup(
                sector_html, max_width=POPUP_WIDTH, min_width=POPUP_WIDTH))

            sector_lyr.add_child(sector_map)

        # Parking
        for parking in area_data['parkings']:
            parking_marker = folium.Marker(
                location=[parking['parking_latitude'],
                          parking['parking_longitude']],
                popup=helpers.generate_parking_html([parking['parking_latitude'],
                                                     parking['parking_longitude']]),
                tooltip='Parking',
                icon=folium.Icon(color='red', icon='info-sign')
            )

            sector_lyr.add_child(parking_marker)

        zoomed_out_icon = BeautifyIcon(icon_shape='marker',
                                       number=len(area_data['sectors'])
                                       )

        sectors_marker = folium.Marker(
            location=[area_data['latitude'], area_data['longitude']],
            tooltip=area_data['name'],
            icon=zoomed_out_icon
        )
        sectors_markers += [sectors_marker]
        # Group areas' markers when zoomed out
        areas_cluster.add_child(sectors_marker)
        zoomed_out_lyr.add_child(areas_cluster)

        area_map.add_child(zoomed_out_lyr)
        area_map.add_child(sector_lyr)
        layers += [(sector_lyr, zoomed_out_lyr)]

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting JavaScript code in the map html
    map_html = area_map.get_root().render()
    for sector_lyr, zoomed_out_lyr in layers:
        # Hide or show layers depending on the zoom level
        map_html = helpers.make_layer_that_hides(
            map_html, area_map.get_name(), sector_lyr.get_name(), DEFAULT_AREA_ZOOM, False, False)
        map_html = helpers.make_layer_that_hides(
            map_html, area_map.get_name(), zoomed_out_lyr.get_name(), DEFAULT_AREA_ZOOM, True, True)
        # Zoom into area when clicking
        for marker in sectors_markers:
            map_html = helpers.zoom_on_click(
                map_html, area_map.get_name(), marker.get_name(), DEFAULT_AREA_ZOOM+1)
    return map_html if return_html else area_map
