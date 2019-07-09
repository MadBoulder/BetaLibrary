
END_OF_SCRIPT = "\n\n</script>"

def generate_sector_html(name, link):
    """
    Generate the html code tat shows the sector name and the link to the playlist
    when clicking on the sector area
    """
    return '<p><b><u>{}</u></b><br><br><a href="{}"target="_blank">Beta videos</a><br></p>'.format(name, link)

def make_layer_that_hides(map_html, map_name, layer_name, zoom_level=15, visible=True, reverse=False):
    """
    Add a piece of JavaScript at the end of the map html that hides/shows
    a layer depending on the zoom level
    """
    hide_by_default = "       map_name.removeLayer(layer_name);\n"
    code_to_inject = """        map_name.on('zoomend', function() {
                if (map_name.getZoom() <= zoom_level){
                    map_name.removeLayer(layer_name);
                }
                else {
                    map_name.addLayer(layer_name);
                }
        });"""

    code_to_inject = code_to_inject.replace("map_name", map_name).replace("layer_name", layer_name).replace("zoom_level", str(zoom_level))
    if reverse:
        code_to_inject = code_to_inject.replace("<=", ">")
    if not visible:
        hide_by_default =  hide_by_default.replace("map_name", map_name).replace("layer_name", layer_name)
        return map_html[:-9] + hide_by_default +  code_to_inject + END_OF_SCRIPT
    return map_html[:-9] + code_to_inject + END_OF_SCRIPT

def zoom_on_click(map_html, map_name, marker_name, zoom_level):
    """
    """
    code_to_inject = """        marker_name.on('click', function(e){
            map_name.setView(e.latlng, zoom_level);
        });"""

    code_to_inject = code_to_inject.replace("map_name", map_name).replace("marker_name", marker_name).replace("zoom_level", str(zoom_level))
    return map_html[:-9] + code_to_inject + END_OF_SCRIPT
