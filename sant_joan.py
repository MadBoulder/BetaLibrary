import numpy as np
import folium
import base64

image_html = '<img src="data:image/png;base64,{}" style="width:{}px;height:{}px;">'.format

### GENERATE MAP ###

# Sant Joan de Vilatorrada

def get_sant_joan_map(html=True):
    sant_joan_map = folium.Map(location=[41.75691,1.7696855],
        zoom_start=16)

    # Parking
    folium.Marker(
        location=[41.7563,1.7716915],
        popup='Parking',
        tooltip='Parking',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(sant_joan_map)

    # La visera
    visera_png = 'images/sant_joan/la_visera.png'
    visera_encoded = base64.b64encode(open(visera_png, 'rb').read())
    visera_image = image_html(visera_encoded.decode(),"200","267")

    visera_html = """
    <p> <b><u>La Visera</u></b>
    <br><a href="https://www.youtube.com/watch?v=XKfRsZFe4Dk  "target="_blank">La Visera (6a)</a>
    """ +"<p>" + visera_image + "</p>"

    visera_popup = folium.Popup(visera_html, max_width=200, min_width=200)

    visera_tooltip = "La Visera"

    folium.Marker(
        location=[41.756717,1.7716345],
        popup=visera_popup,
        tooltip=visera_tooltip,
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(sant_joan_map)

    return sant_joan_map.get_root().render() if html else sant_joan_map
