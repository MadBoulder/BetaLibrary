import numpy as np
import folium
from folium.plugins import MarkerCluster
# import base64
import json
import os

POPUP_WIDTH = 100

# image_html = '<img src="data:image/png;base64,{}" style="width:{}px;height:{}px;">'.format

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
        sector_html = '<p> <b><u>{}</u></b><br><a href="{}"target="_blank">Beta videos</a</p>'.format(sector['name'], sector['link'])
        sector_map.add_child(folium.Popup(sector_html,
            max_width=POPUP_WIDTH, min_width=POPUP_WIDTH))
        sector_map.add_to(area_map)

    # Parking
    folium.Marker(
        location=[area_data['parking_latitude'],area_data['parking_longitude']],
        popup='Parking',
        tooltip='Parking',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(area_map)

    # marker_cluster = MarkerCluster().add_to(area_map)

    # # Create and add boulder markers
    # boulders = area_data['boulders']
    # for boulder in boulders: 
    #     boulder_image = image_html(base64.b64encode(open(boulder['image'], 'rb').read()).decode(), boulder['width'], boulder['height'])
    #     boulder_lines = ['<br><a href="'+line['link']+'"target="_blank">'+line['name']+'</a>' for line in boulder['lines']]
    #     lines_html = '<p> <b><u>'+ boulder['name'] +'</u></b><br>'+('').join(boulder_lines)+'</p>'
    #     boulder_html = lines_html + '<p>' + boulder_image + '</p>'

    #     boulder_popup = folium.Popup(boulder_html, max_width=POPUP_WIDTH, min_width=POPUP_WIDTH)

    #     boulder_tooltip = boulder['name']

    #     folium.Marker(
    #         location=[boulder['latitude'],boulder['longitude']],
    #         popup=boulder_popup,
    #         tooltip=boulder_tooltip,
    #         icon=folium.Icon(color='green', icon='info-sign')
    #     ).add_to(marker_cluster)

    return area_map.get_root().render() if return_html else area_map
