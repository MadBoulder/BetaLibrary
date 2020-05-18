import numpy as np
import folium
from folium.plugins import MarkerCluster, BeautifyIcon, Fullscreen
from folium.features import CustomIcon
import json
import os
import js_helpers

POPUP_WIDTH = 100
WIDTH_MULTIPLIER = 15
DEFAULT_AREA_ZOOM = 10
SECTOR_OPACITY = 0.6
MARKER_SIZE = 32
ICON_SIZE = 24
PLACEHOLDER = '_placeholder'
APPROX_PLACEHOLDER = 'approx_placeholder'

#####################
### GENERATE MAPS ###
#####################

def load_map(area, datafile, generate_ids, return_html=True):
    """
    Create a map for a bouldering zone that shows the GEOJSON data, names and
    links to video playlists of its sectors as well as the parking areas. All
    this data should be provided via a JSON file
    """
    generate_ids.reset_seed()
    area_data = {}
    with open(datafile, encoding='utf-8') as data:
        area_data = json.load(data)

    area_map = folium.Map(location=[area_data['latitude'], area_data['longitude']],
                          zoom_start=area_data['zoom'])
    area_map._id = generate_ids.next_id() # reassign id
    for child in area_map._children.values():
        child._id = generate_ids.next_id()
    tile_layer = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        name="Satellite",
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    )
    tile_layer._id = generate_ids.next_id() # reassign id
    tile_layer.add_to(area_map)

    # Add fullscreen button to map
    fs = Fullscreen()
    fs._id = generate_ids.next_id() 
    fs.add_to(area_map)

    sectors = area_data['sectors']
    # Create a Folium feature group for this layer, since we will be displaying multiple layers
    sector_lyr = folium.FeatureGroup(name='Zone Markers')
    sector_lyr._id = generate_ids.next_id() # reassign id
    
    for sector in sectors:
        if not sector['sector_data'] or not sector['link']:
            continue
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
        sector_map._id = generate_ids.next_id() # reassign id
        sector_html = js_helpers.generate_sector_html(
            sector['name'], sector['link'])
        sector_popup = folium.Popup(
            sector_html,
            max_width=POPUP_WIDTH,
            min_width=POPUP_WIDTH
        )
        sector_popup._id = generate_ids.next_id() # reassign id
        for child in sector_popup._children.values():
            child._id = generate_ids.next_id()

        sector_map.add_child(sector_popup)

        sector_lyr.add_child(sector_map)

    # Parking areas
    for parking in area_data['parkings']:
        parking_icon = CustomIcon(
            'static/images/icons/parking.png',
            icon_size=(ICON_SIZE, ICON_SIZE)
        )
        parking_icon._id = generate_ids.next_id() # reassign id
        parking_marker = folium.Marker(
            location=[parking['parking_latitude'],
                      parking['parking_longitude']],
            popup=js_helpers.generate_parking_html([parking['parking_latitude'],
                                                    parking['parking_longitude']]),
            tooltip='Parking',
            icon=parking_icon
        )
        parking_marker._id = generate_ids.next_id() # reassign id
        for child in parking_marker._children.values():
            child._id = generate_ids.next_id()

        sector_lyr.add_child(parking_marker)

    # Approximation
    if area_data.get('approximation', None) is not None:
        import gpxpy
        import gpxpy.gpx

        approximation_geojson = {
            "type": "Feature",
            "properties": {
                "stroke": "#1f1a95",
                "stroke-opacity": 1,
                "stroke-width": 2
            },
            "geometry": {
                "type": "LineString",
                "coordinates": []
            }
        }

        gpx_path = 'data/zones/' + area + '/' + area_data.get('approximation')
        with open(gpx_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                            approximation_geojson['geometry']['coordinates'].append([point.longitude, point.latitude])

        zone_approximation = folium.GeoJson(
            approximation_geojson,
            name="Approximation",
            tooltip=APPROX_PLACEHOLDER,
            style_function=lambda x: {
                'color': x['properties']['stroke'],
                'weight': x['properties']['stroke-width'],
                'opacity': SECTOR_OPACITY,
                'fillColor': x['properties']['stroke'],
            }
        )
        zone_approximation._id = generate_ids.next_id() # reassign id
        sector_lyr.add_child(zone_approximation)

    # Sectors
    zoomed_out_lyr = folium.FeatureGroup(name='Sector Markers')
    zoomed_out_lyr._id = generate_ids.next_id() # reassign id
    zoomed_out_icon = CustomIcon(
        'static/images/marker/marker.png', icon_size=(MARKER_SIZE, MARKER_SIZE))
    zoomed_out_icon._id = generate_ids.next_id() # reassign id
    sectors_marker = folium.Marker(
        location=[area_data['latitude'], area_data['longitude']],
        tooltip=area_data['name'],
        icon=zoomed_out_icon
    )
    sectors_marker._id = generate_ids.next_id() # reassign id
    zoomed_out_lyr.add_child(sectors_marker)

    area_map.add_child(zoomed_out_lyr)
    area_map.add_child(sector_lyr)

    layer_control = folium.LayerControl()
    layer_control._id = generate_ids.next_id() # reassign id
    layer_control.add_to(area_map)

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting JavaScript code in the map html
    map_html = area_map.get_root().render()
    map_html = js_helpers.make_layer_that_hides(
        map_html, area_map.get_name(), sector_lyr.get_name(), DEFAULT_AREA_ZOOM)
    map_html = js_helpers.make_layer_that_hides(
        map_html, area_map.get_name(), zoomed_out_lyr.get_name(), DEFAULT_AREA_ZOOM, False, True)
    # Zoom into area when clicking
    map_html = js_helpers.zoom_on_click(
        map_html, area_map.get_name(), sectors_marker.get_name(), DEFAULT_AREA_ZOOM+1)
    
    map_html = js_helpers.enable_links_from_iframe(map_html)
    map_html = js_helpers.replace_maps_placeholder(map_html)
    map_html = js_helpers.replace_approx_placeholders_for_translations(map_html, APPROX_PLACEHOLDER)
    # replace the ids of all the html tags
    map_html = js_helpers.replace_tag_ids(map_html, ['html'], generate_ids)
    return map_html if return_html else area_map


def load_general_map(datafiles, generate_ids, return_html=True):
    """
    Create a map that contains all the zones provided by the list of datafiles
    i.e. all areas combined in one map. This map only shows the markers that 
    indicate the 
    """
    generate_ids.reset_seed()
    area_map = folium.Map(
        location=[
            -23.0390625,
            -18.299051014581817
        ],
        zoom_start=2
    )
    area_map._id = generate_ids.next_id() # reassign id
    for child in area_map._children.values():
        child._id = generate_ids.next_id()

    tile_layer = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        name="Satellite",
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    )
    tile_layer._id = generate_ids.next_id() # reassign id
    tile_layer.add_to(area_map)
    
    # Add fullscreen button to map
    fs = Fullscreen()
    fs._id = generate_ids.next_id() 
    fs.add_to(area_map)

    layers = []
    sectors_markers = []
    placeholders = []

    # Sectors layer
    zoomed_out_lyr = folium.FeatureGroup(name='Sector Markers')
    zoomed_out_lyr._id = generate_ids.next_id() # reassign id
    areas_cluster = MarkerCluster()
    areas_cluster._id = generate_ids.next_id() # reassign id

    for areadatafile in datafiles:
        area_data = {}
        with open(areadatafile, encoding='utf-8') as data:
            area_data = json.load(data)

        # sectors = area_data['sectors']
        # # Create a Folium feature group for this layer, since we will be displaying multiple layers
        # sector_lyr = folium.FeatureGroup(name='sectors_layer')
        # for sector in sectors:
        #     sector_map = folium.GeoJson(
        #         os.path.dirname(os.path.abspath(areadatafile)) +
        #         sector['sector_data'],
        #         name=sector['name'],
        #         tooltip=sector['name'],
        #         style_function=lambda x: {
        #             'color': x['properties']['stroke'],
        #             'weight': x['properties']['stroke-width'],
        #             'opacity': SECTOR_OPACITY,
        #             'fillColor': x['properties']['stroke'],
        #         }
        #     )
        #     sector_html = helpers.generate_sector_html(
        #         sector['name'], sector['link'])
        #     sector_map.add_child(folium.Popup(
        #         sector_html, max_width=POPUP_WIDTH, min_width=POPUP_WIDTH))

        #     sector_lyr.add_child(sector_map)

        # Parking
        # for parking in area_data['parkings']:
        #     parking_marker = folium.Marker(
        #         location=[parking['parking_latitude'],
        #                   parking['parking_longitude']],
        #         popup=helpers.generate_parking_html([parking['parking_latitude'],
        #                                              parking['parking_longitude']]),
        #         tooltip='Parking',
        #         icon=folium.Icon(color='red', icon='info-sign')
        #     )

        #     sector_lyr.add_child(parking_marker)

        zoomed_out_icon = CustomIcon(
            'static/images/marker/marker.png', icon_size=(MARKER_SIZE, MARKER_SIZE))
        zoomed_out_icon._id = generate_ids.next_id() # reassign id
        html_redirect, _ = os.path.splitext(
            os.path.basename(os.path.normpath(areadatafile)))
        area_name = os.path.splitext(os.path.basename(areadatafile))[0]
        placeholder = area_name + PLACEHOLDER
        popup_html = folium.Html(js_helpers.generate_area_popup_html(
            area_data['name'], area_name, html_redirect, placeholder), script=True)
        popup_html._id = generate_ids.next_id() # reassign id
        zone_popup = folium.Popup(
            popup_html, max_width=len(area_data['name'])*10)
        zone_popup._id = generate_ids.next_id() # reassign id
        placeholders.append(placeholder)

        sectors_marker = folium.Marker(
            location=[area_data['latitude'], area_data['longitude']],
            tooltip=area_data['name'],
            icon=zoomed_out_icon,
            popup=zone_popup,
        )
        sectors_marker._id = generate_ids.next_id() # reassign id
        sectors_markers += [sectors_marker]
        # Group areas' markers when zoomed out
        areas_cluster.add_child(sectors_marker)
        zoomed_out_lyr.add_child(areas_cluster)

        area_map.add_child(zoomed_out_lyr)
        # area_map.add_child(sector_lyr)
        # layers += [(sector_lyr, zoomed_out_lyr)]


    layer_control = folium.LayerControl()
    layer_control._id = generate_ids.next_id() # reassign id
    layer_control.add_to(area_map)

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting or editing JavaScript code in the map html
    map_html = area_map.get_root().render()
    # for sector_lyr, zoomed_out_lyr in layers:
    #     # Hide or show layers depending on the zoom level
    #     map_html = helpers.make_layer_that_hides(
    #         map_html, area_map.get_name(), sector_lyr.get_name(), DEFAULT_AREA_ZOOM, False, False)
    #     map_html = helpers.make_layer_that_hides(
    #         map_html, area_map.get_name(), zoomed_out_lyr.get_name(), DEFAULT_AREA_ZOOM, True, True)
    #     # Zoom into area when clicking
    #     for marker in sectors_markers:
    #         map_html = helpers.zoom_on_click(
    #             map_html, area_map.get_name(), marker.get_name(), DEFAULT_AREA_ZOOM+1)
    map_html = js_helpers.replace_custom_placeholders(map_html, placeholders)
    map_html = js_helpers.replace_tag_ids(map_html, ['html'], generate_ids)
    return map_html if return_html else area_map
