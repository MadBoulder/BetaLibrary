import numpy as np
import folium
import webbrowser
import base64

import temp_server

SERVER_ADDRESS = '{host}:{port}'.format(host=temp_server.HOST, port=temp_server.PORT)
FULL_SERVER_ADDRESS = 'http://' + SERVER_ADDRESS
image_html = '<img src="data:image/png;base64,{}" style="width:{}px;height:{}px;">'.format

### GENERATE MAP ###

# Savassona
savassona_map = folium.Map(location=[41.9574367, 2.3402503],
    zoom_start=16)

# Parking
folium.Marker(
    location=[41.9561832,2.3397532],
    popup='Parking',
    tooltip='Parking',
    icon=folium.Icon(color='red', icon='info-sign')
).add_to(savassona_map)

# El Dau
dau_png = 'images/dau.png'
dau_encoded = base64.b64encode(open(dau_png, 'rb').read())
dau_image = image_html(dau_encoded.decode(),"200","150")

dau_html = """
<p> <b><u>El Dau</u></b>
<br><a href=" https://www.youtube.com/watch?v=3gczKMUudtQ "target="_blank"> Lance del Dau (6b) </a>
<br><a href=" https://www.youtube.com/watch?v=Pijky6do7Bg "target="_blank"> El Morro del Dau (6a) </a>
<br><a href=" https://www.youtube.com/watch?v=KkJKPMYRoq0 "target="_blank"> Trave del Dau (5+/6a) </a>
<br><a href=" https://www.youtube.com/watch?v=bI5mqGnPpfw "target="_blank"> Problem 4 (4) </a></p>
""" +"<p>" + dau_image + "</p>"

dau_popup = folium.Popup(dau_html, max_width=200, min_width=200)

dau_tooltip = "El Dau"

folium.Marker(
    location=[41.959015,2.3416425],
    popup=dau_popup,
    tooltip=dau_tooltip,
    icon=folium.Icon(color='green', icon='info-sign')
).add_to(savassona_map)

# Hommo Sapiens
hommo_sapiens_png = 'images/hommo_sapiens.png'
hommo_sapiens_encoded = base64.b64encode(open(hommo_sapiens_png, 'rb').read())
hommo_sapiens_image = image_html(hommo_sapiens_encoded.decode(), "156", "205")

sapiens_html = """
<p> <b><u>Hommo Sapiens</u></b>
<br><a href=" https://www.youtube.com/watch?v=D4eqY1JsFWc "target="_blank"> Hommo Herektus (7c/+) </a>
<br><a href=" https://www.youtube.com/watch?v=is7UVvJiWrw "target="_blank"> Tanga Vermell (6c) </a>
<br><a href=" https://www.youtube.com/watch?v=h5NQWO9G1oU "target="_blank"> Morfosintaxis (6b) </a></p>
""" +"<p>" + hommo_sapiens_image + "</p>"

sapiens_popup = folium.Popup(sapiens_html, max_width=200, min_width=200)

sapiens_tooltip = "Hommo Sapiens"

folium.Marker(
    location=[41.958615,2.3400375],
    popup=sapiens_popup,
    tooltip=sapiens_tooltip,
    icon=folium.Icon(color='green', icon='info-sign')
).add_to(savassona_map)


def run_html_server(html_data=None):

    if html_data is None:
        html_data = """
        <!DOCTYPE html>
        <html>
        <head>
        <title>Page Title</title>
        </head>
        <body>
        <h1>This is a Heading</h1>
        <p>This is a paragraph.</p>
        </body>
        </html>
        """

    # open in a browser URL and see a result
    webbrowser.open(FULL_SERVER_ADDRESS)

    # run server
    temp_server.TemproraryHttpServer('html', html_data)

### --------------------- ###

# Save the visualization into the temp file and render it
from tempfile import NamedTemporaryFile
tmp = NamedTemporaryFile()
savassona_map.save(tmp.name)
savassona_map.save("templates/savassona.html")

with open(tmp.name) as f:
    savassona_map_html = f.read()

run_html_server(savassona_map_html)
