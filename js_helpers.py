import helpers
import re

END_OF_SCRIPT = "\n\n</script>"
PLACEHOLDER = '_placeholder'
GM_PLACEHOLDER = 'GM_PH'


def replace_tag_ids(map_html, tags_to_replace, generate_ids):
    """
    Control tags ids
    """
    for tag_to_replace in tags_to_replace:
        html_tags = re.findall(tag_to_replace+'_\w*', map_html)
        # find tag indexes
        positions = []
        tags = set(html_tags)  # remove duplicates
        for tag in tags:
            position = map_html.index(tag)
            positions.append((tag, position))
        # sort by position
        sorted_tags = sorted(positions, key=lambda x: x[1])
        replacements = {i: tag_to_replace+'_'+generate_ids.next_id()
                        for i, v in sorted_tags}
        for to_replace, index in sorted_tags:
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
    """
    return map_html.replace(GM_PLACEHOLDER, '{{ _("Open in") }}')


def enable_links_from_iframe(map_html):
    """
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


def generate_track_html(area, track_name):
    """
    Generate the html code that adds the link to the downloadable approximation
    track
    """
    track_url = '/download/' + area + '/' + track_name
    return '<a href="{}">Track</a><br>'.format(track_url)


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
    placeholders.sort(key=lambda s: len(s))
    placeholders.reverse()
    for placeholder in placeholders:
        variable = placeholder.replace(PLACEHOLDER, '')
        map_html = map_html.replace(placeholder, '{{'+variable+'}}')
    return map_html


def replace_sectors_placeholders_for_translations(map_html, sector_placeholder='sector_placeholder'):
    """
    Replace the sector's text placeholder in the HTML by the localized string.
    This is to avoid the render() function throwing an error when processing the map's html
    """
    map_html = map_html.replace(sector_placeholder, '{{ _("Sectors") }}')
    return map_html


def replace_approx_placeholders_for_translations(map_html, approx_placeholder='approx_placeholder'):
    """
    Replace the sector's text placeholder in the HTML by the localized string.
    This is to avoid the render() function throwing an error when processing the map's html
    """
    map_html = map_html.replace(
        approx_placeholder, '{{ _("Approximation\n(Click to download track)") }}')
    return map_html


def generate_area_popup_html(area_name, area_filename, redirect, placeholder):
    """
    Generate the html code tat shows the zone name and a link
    to the page, as well as the number of videos of the zone

    the placeholder variable should be the name of the zone + the
    placeholder indicator. This value will be replaced by the number
    of beta videos when rendering the pop up
    """
    sector_count = helpers.count_sectors_in_zone(area_filename)
    return '<p><a href="'+'/'+redirect+'"target="_blank">'+area_name+'</a></p><p>sector_placeholder: '+str(sector_count)+'<br/> Beta Videos: '+placeholder+'</p>'


def remove_geojson_zoom_on_click(map_html):
    """
    Remove calls to fitBounds in GeoJSON features to avoid zooming in when clicking
    """
    map_html = re.sub(
        r'(map_\w+.fitBounds\(e.target.getBounds\(\)\);)', '', map_html)
    return map_html
