
def generate_sector_html(name, link):
    """
    Generate the html code tat shows the sector name and the link to the playlist
    when clicking on the sector area
    """
    return '<p> <b><u>{}</u></b><br><a href="{}"target="_blank">Beta videos</a</p>'.format(name, link)

def make_layer_that_hides(map_html, map_name, layer_name, zoom_level=15):
    """
    Add a piece of JavaScript at the end of the map html that hides/shows
    a layer depending on the zoom level
    """
    java = """        map_name.on('zoomend', function() {
                if (map_name.getZoom() < zoom_level){
                    map_name.removeLayer(layer_name);
                }
                else {
                    map_name.addLayer(layer_name);
                }
        });"""

    java = java.replace("map_name", map_name).replace("layer_name", layer_name).replace("zoom_level", str(zoom_level))
    return map_html[:-9] + java + "\n\n</script>"