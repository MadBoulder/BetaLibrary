import folium
from folium.plugins import MarkerCluster, Fullscreen
from folium.features import CustomIcon
import json
import os
import utils.js_helpers

POPUP_WIDTH = 100
WIDTH_MULTIPLIER = 15
DEFAULT_AREA_ZOOM = 10
SECTOR_OPACITY = 0.6
MARKER_SIZE = 32
ICON_SIZE = 24
PLACEHOLDER = '_placeholder'
APPROX_PLACEHOLDER = 'approx_placeholder'
BETA_VIDEOS_TEXT = 'Beta Videos: '

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
    area_map._id = generate_ids.next_id()  # reassign id
    for child in area_map._children.values():
        child._id = generate_ids.next_id()
    tile_layer = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        name='Satellite',
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    )
    tile_layer._id = generate_ids.next_id()  # reassign id
    tile_layer.add_to(area_map)

    # Add fullscreen button to map
    fs = Fullscreen()
    fs._id = generate_ids.next_id()
    fs.add_to(area_map)

    sectors = area_data.get('sectors', [])
    # Create a Folium feature group for this layer, since we will be displaying multiple layers
    sector_lyr = folium.FeatureGroup(name='Parking Markers')
    sector_lyr._id = generate_ids.next_id()  # reassign id

    #for sector in sectors:
    #    if not sector['sector_data'] or not sector['link']:
    #        continue
    #    sector_map = folium.GeoJson(
    #        os.path.dirname(os.path.abspath(datafile))+sector['sector_data'],
    #        name=sector['name'],
    #        tooltip=sector['name'],
    #        style_function=lambda x: {
    #            'color': x['properties']['stroke'],
    #            'weight': x['properties']['stroke-width'],
    #            'opacity': SECTOR_OPACITY,
    #            'fillColor': x['properties']['stroke'],
    #        }
    #    )
    #    sector_map._id = generate_ids.next_id()  # reassign id
    #    sector_html = utils.js_helpers.generate_sector_html(
    #        sector['name'], sector['link'])
    #    sector_popup = folium.Popup(
    #        sector_html,
    #        max_width=POPUP_WIDTH,
    #        min_width=POPUP_WIDTHº
    #    )
    #    sector_popup._id = generate_ids.next_id()  # reassign id
    #    for child in sector_popup._children.values():
    #        child._id = generate_ids.next_id()
    #
    #    sector_map.add_child(sector_popup)
    #
    #    sector_lyr.add_child(sector_map)
    #
    # Parking areas
    if 'parkings' in area_data and area_data['parkings']:
        for parking in area_data['parkings']:
            parking_icon = CustomIcon(
                'static/images/icons/parking.png',
                icon_size=(ICON_SIZE, ICON_SIZE)
            )
            parking_icon._id = generate_ids.next_id()  # reassign id
            parking_marker = folium.Marker(
                location=[parking['parking_latitude'],
                        parking['parking_longitude']],
                popup=utils.js_helpers.generate_parking_html([parking['parking_latitude'],
                                                            parking['parking_longitude']]),
                tooltip='Parking',
                icon=parking_icon
            )
            parking_marker._id = generate_ids.next_id()  # reassign id
            for child in parking_marker._children.values():
                child._id = generate_ids.next_id()

            sector_lyr.add_child(parking_marker)

    # Approximation
    if area_data.get('approximation', None) is not None:
        import gpxpy
        import gpxpy.gpx

        approximation_geojson = {
            'type': 'Feature',
            'properties': {
                'stroke': '#1f1a95',
                'stroke-opacity': 1,
                'stroke-width': 2
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': []
            }
        }

        gpx_path = 'data/zones/' + area + '/' + area_data.get('approximation')
        with open(gpx_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        approximation_geojson['geometry']['coordinates'].append(
                            [point.longitude, point.latitude])

        zone_approximation = folium.GeoJson(
            approximation_geojson,
            name='Approximation',
            tooltip=APPROX_PLACEHOLDER,
            style_function=lambda x: {
                'color': x['properties']['stroke'],
                'weight': x['properties']['stroke-width'],
                'opacity': SECTOR_OPACITY,
                'fillColor': x['properties']['stroke'],
            }
        )
        zone_approximation._id = generate_ids.next_id()  # reassign id

        zone_approx_html = utils.js_helpers.generate_file_download_html(
            area, area_data.get('approximation'), 'Track')

        track_popup = folium.Popup(
            zone_approx_html,
            max_width=POPUP_WIDTH,
            min_width=POPUP_WIDTH
        )
        track_popup._id = generate_ids.next_id()  # reassign id

        for child in track_popup._children.values():
            child._id = generate_ids.next_id()

        zone_approximation.add_child(track_popup)

        sector_lyr.add_child(zone_approximation)

    # Sectors
    zoomed_out_lyr = folium.FeatureGroup(name='Zone Marker')
    zoomed_out_lyr._id = generate_ids.next_id()  # reassign id
    zoomed_out_icon = CustomIcon(
        'static/images/marker/marker.webp', icon_size=(MARKER_SIZE, MARKER_SIZE))
    zoomed_out_icon._id = generate_ids.next_id()  # reassign id
    sectors_marker = folium.Marker(
        location=[area_data['latitude'], area_data['longitude']],
        tooltip=area_data['name'],
        icon=zoomed_out_icon
    )
    sectors_marker._id = generate_ids.next_id()  # reassign id
    zoomed_out_lyr.add_child(sectors_marker)

    area_map.add_child(zoomed_out_lyr)
    area_map.add_child(sector_lyr)

    layer_control = folium.LayerControl()
    layer_control._id = generate_ids.next_id()  # reassign id
    layer_control.add_to(area_map)

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting JavaScript code in the map html
    map_html = area_map.get_root().render()
    map_html = utils.js_helpers.make_layer_that_hides(
        map_html, area_map.get_name(), sector_lyr.get_name(), DEFAULT_AREA_ZOOM)
    #map_html = utils.js_helpers.make_layer_that_hides(
    #    map_html, area_map.get_name(), zoomed_out_lyr.get_name(), DEFAULT_AREA_ZOOM, False, True)
    # Zoom into area when clicking
    map_html = utils.js_helpers.zoom_on_click(
        map_html, area_map.get_name(), sectors_marker.get_name(), DEFAULT_AREA_ZOOM+1)

    map_html = utils.js_helpers.enable_links_from_iframe(map_html)
    map_html = utils.js_helpers.replace_maps_placeholder(map_html)
    map_html = utils.js_helpers.replace_approx_placeholders_for_translations(
        map_html, APPROX_PLACEHOLDER)
    # Avoid zooming in when clicking on a sector area
    map_html = utils.js_helpers.remove_geojson_zoom_on_click(map_html)
    # replace the ids of all the html tags
    map_html = utils.js_helpers.replace_tag_ids(
        map_html, ['html'], generate_ids)
    return map_html if return_html else area_map


def load_general_map(zone_data, generate_ids, return_html=True):
    """
    Create a map that contains all the zones provided by the list of zone_data
    i.e. all areas combined in one map. This map only shows the markers that 
    indicate an existing area.
    """
    generate_ids.reset_seed()
    area_map = folium.Map(
        location=[
            15.417195,
            -15.184135
        ],
        zoom_start=3
    )
    area_map._id = generate_ids.next_id()  # reassign id
    for child in area_map._children.values():
        child._id = generate_ids.next_id()

    tile_layer = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        name='Satellite',
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    )
    tile_layer._id = generate_ids.next_id()  # reassign id
    tile_layer.add_to(area_map)

    # Add fullscreen button to map
    fs = Fullscreen()
    fs._id = generate_ids.next_id()
    fs.add_to(area_map)

    # Areas layer
    zoomed_out_lyr = folium.FeatureGroup(name='Areas Markers')
    zoomed_out_lyr._id = generate_ids.next_id()  # reassign id
    areas_cluster = MarkerCluster()
    areas_cluster._id = generate_ids.next_id()  # reassign id

    for zone in zone_data['items']:
        zoomed_out_icon = CustomIcon(
            'static/images/marker/marker.webp', icon_size=(MARKER_SIZE, MARKER_SIZE))
        zoomed_out_icon._id = generate_ids.next_id()  # reassign id
        playlists = utils.zone_helpers.get_playlists_from_zone(zone['zone_code'])
        popup_html = folium.Html(utils.js_helpers.generate_area_popup_html(
            zone['name'], zone['zone_code'], playlists['video_count']), script=True)
        popup_html._id = generate_ids.next_id()  # reassign id
        zone_popup = folium.Popup(
            popup_html, max_width=max(len(zone['name']), len(BETA_VIDEOS_TEXT))*10)
        zone_popup._id = generate_ids.next_id()  # reassign id

        area_marker = folium.Marker(
            location=[zone['latitude'], zone['longitude']],
            tooltip=zone['name'],
            icon=zoomed_out_icon,
            popup=zone_popup,
        )
        area_marker._id = generate_ids.next_id()  # reassign id
        # Group areas' markers when zoomed out
        areas_cluster.add_child(area_marker)
        zoomed_out_lyr.add_child(areas_cluster)

        area_map.add_child(zoomed_out_lyr)

    layer_control = folium.LayerControl()
    layer_control._id = generate_ids.next_id()  # reassign id
    layer_control.add_to(area_map)

    # Since folium does not support all the functionalities we need
    # we obtain them by injecting or editing JavaScript code in the map html
    map_html = area_map.get_root().render()
    map_html = utils.js_helpers.replace_tag_ids(
        map_html, ['html'], generate_ids)
    return map_html if return_html else area_map
