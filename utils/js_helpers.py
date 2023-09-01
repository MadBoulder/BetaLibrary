import utils.helpers
import re

PLACEHOLDER = '_placeholder'
GM_PLACEHOLDER = 'GM_PH'


def replace_tag_ids(map_html, tags_to_replace, generate_ids):
    """
    Control tags ids. This is a way to control id generation
    and ensure the same IDs are used each time the tags are
    generated. This is to make the changes more git friendly.
    """
    for tag_to_replace in tags_to_replace:
        html_tags = re.findall(tag_to_replace + r'_\w*', map_html)
        # find tag indexes
        positions = []
        tags = set(html_tags)  # remove duplicates
        for tag in tags:
            position = map_html.index(tag)
            positions.append((tag, position))
        # sort by position
        # sorted_tags -> list([to_replace, index])
        sorted_tags = sorted(positions, key=lambda x: x[1])
        replacements = {i: tag_to_replace+'_'+generate_ids.next_id()
                        for i, v in sorted_tags}
        for to_replace, _ in sorted_tags:
            map_html = map_html.replace(to_replace, replacements[to_replace])
    return map_html


def generate_parking_html(coordinates):
    """
    Generate parking popup text
    """
    gm_url = "https://www.google.com/maps/search/?api=1&query={},{}".format(
        str(coordinates[0]), str(coordinates[1]))
    return '<p>{}<br><br>{}, {}<br></p><p><a href="{}" target="_blank">GM_PH Google Maps</a></p>'.format('Parking', round(coordinates[0], 4), round(coordinates[1], 4), gm_url)


def replace_maps_placeholder(map_html):
    """
    Replace the maps placeholder by the current text we want to show
    """
    return map_html.replace(GM_PLACEHOLDER, '{{ _("Open in") }}')


def enable_links_from_iframe(map_html):
    """
    Insert links in iframes
    """
    code_to_inject = """<head>    
    <base target="_blank">"""
    return map_html.replace('<head>', code_to_inject)


def generate_sector_html(name, link):
    """
    Generate the html code that shows the sector name and the link to the playlist
    when clicking on the sector area
    """
    return '<p><b><u>{}</u></b><br><br><a href="{}" target="_blank">Beta videos</a><br></p>'.format(name, link)


def generate_file_download_html(area, filename, text_to_show):
    """
    Generate the html code that adds the link to the downloadable file
    """
    return '<a href="{}">{}</a><br>'.format(utils.helpers.generate_download_url(area, filename), text_to_show)

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
        });\n"""

    code_to_inject = code_to_inject.replace("map_name", map_name).replace(
        "layer_name", layer_name).replace("zoom_level", str(zoom_level))
    script_tag_position = map_html.rfind("</script>")
        
    if reverse:
        code_to_inject = code_to_inject.replace("<=", ">")
    if not visible:
        hide_by_default = hide_by_default.replace(
            "map_name", map_name).replace("layer_name", layer_name)
        return map_html[:script_tag_position] + hide_by_default + code_to_inject + map_html[script_tag_position:]
    return map_html[:script_tag_position] + code_to_inject + map_html[script_tag_position:]


def zoom_on_click(map_html, map_name, marker_name, zoom_level):
    """
    Inject a piece of js that applies zoom to the map when 
    clicking the marker passed as an argument
    """
    code_to_inject = """        marker_name.on('click', function(e){
            map_name.setView(e.latlng, zoom_level);
        });\n"""

    code_to_inject = code_to_inject.replace("map_name", map_name).replace(
        "marker_name", marker_name).replace("zoom_level", str(zoom_level))
    script_tag_position = map_html.rfind("</script>")
    return map_html[:script_tag_position] + code_to_inject + map_html[script_tag_position:]


def replace_approx_placeholders_for_translations(map_html, approx_placeholder='approx_placeholder'):
    """
    Replace the sector's text placeholder in the HTML by the localized string.
    This is to avoid the render() function throwing an error when processing the map's html
    """
    map_html = map_html.replace(
        approx_placeholder, '{{ _("Approximation\n(Click to download track)") }}')
    return map_html


def generate_area_popup_html(area_name, area_code, area_videos):
    """
    Generate the html code tat shows the zone name and a link
    to the page, as well as the number of videos of the zone

    the placeholder variable should be the name of the zone + the
    placeholder indicator. This value will be replaced by the number
    of beta videos when rendering the pop up
    """
    return '<p><a href="'+'/'+area_code+'"target="_blank">'+area_name+'</a></p><p>Beta Videos: '+ str(area_videos) +'</p>'


def remove_geojson_zoom_on_click(map_html):
    """
    Remove calls to fitBounds in GeoJSON features to avoid zooming in when clicking
    """
    map_html = re.sub(
        r'(map_\w+.fitBounds\(e.target.getBounds\(\)\);)', '', map_html)
    return map_html
