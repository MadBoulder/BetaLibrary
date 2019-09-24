END_OF_SCRIPT = "\n\n</script>"
PLACEHOLDER = '_placeholder'


def generate_parking_html(coordinates):
    """
    Generate parking popup text
    """
    return '<p>{}<br><br>{}, {}<br></p>'.format('Parking', round(coordinates[0], 4), round(coordinates[1], 4))


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

    code_to_inject = code_to_inject.replace("map_name", map_name).replace(
        "layer_name", layer_name).replace("zoom_level", str(zoom_level))
    if reverse:
        code_to_inject = code_to_inject.replace("<=", ">")
    if not visible:
        hide_by_default = hide_by_default.replace(
            "map_name", map_name).replace("layer_name", layer_name)
        return map_html[:-9] + hide_by_default + code_to_inject + END_OF_SCRIPT
    return map_html[:-9] + code_to_inject + END_OF_SCRIPT


def zoom_on_click(map_html, map_name, marker_name, zoom_level):
    """
    Inject a piece of js that applies zoom to the map when 
    clicking the marker passed as an argument
    """
    code_to_inject = """        marker_name.on('click', function(e){
            map_name.setView(e.latlng, zoom_level);
        });"""

    code_to_inject = code_to_inject.replace("map_name", map_name).replace(
        "marker_name", marker_name).replace("zoom_level", str(zoom_level))
    return map_html[:-9] + code_to_inject + END_OF_SCRIPT


def replace_custom_placeholders(map_html, placeholders):
    """
    This method replaces the custom defined placeholders by jinja's
    default variable placeholders ({{var_name}}). A method is defined
    for this because when adding custom html (via folium.Html) to the already 
    folium generated html it gets executed and the curly braces are lost.
    After that, the specified variables in the template are no longer
    recognized and the values are not updated. 
    """
    for placeholder in placeholders:
        variable = placeholder.replace(PLACEHOLDER, '')
        map_html = map_html.replace(placeholder, '{{'+variable+'}}')
    return map_html


def generate_area_popup_html(area_name, redirect, placeholder):
    """
    Generate the html code tat shows the zone name and a link
    to the page, as well as the number of videos of the zone

    the placeholder variable should be the name of the zone + the
    placeholder indicator. This value will be replaced by the number
    of beta videos when rendering the pop up
    """
    return '<p><a href="'+'/'+redirect+'"target="_blank">'+area_name+'</a><br></p><p>Beta Videos: '+placeholder+'</p>'
