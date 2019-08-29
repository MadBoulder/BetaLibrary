import urllib.request
import json


END_OF_SCRIPT = "\n\n</script>"
PLACEHOLDER = '_placeholder'


class bidict(dict):
    """
    Bidirectional dictionary. Given a normal Python dict it enables to retrieve values by
    key and keys by value
    """
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key], []).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)

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
    """
    for placeholder in placeholders:
        variable = placeholder.replace(PLACEHOLDER, '')
        map_html = map_html.replace(placeholder, '{{'+variable+'}}')
    return map_html


def get_videos_from_channel(channel_id="UCX9ok0rHnvnENLSK7jdnXxA", num_videos=6):
    """
    Obtain the num_videos latest videos from MadBoulder's youtube channel
    """
    api_key = None
    with open("credentials.txt", "r") as f:
        api_key = f.read()

    base_video_url = '//www.youtube.com/embed/'
    base_search_url = 'https://www.googleapis.com/youtube/v3/search?'

    url = base_search_url + \
        'key={}&channelId={}&part=snippet,id&order=date&maxResults={}&type=video'.format(
            api_key, channel_id, str(num_videos))

    video_links = []
    inp = urllib.request.urlopen(url)
    resp = json.load(inp)
    for i in resp['items']:
        if i['id']['kind'] == "youtube#video":
            video_links.append(base_video_url + i['id']['videoId'])
    return video_links


def get_number_of_videos_from_playlists_file(file):
    """
    """
    api_key = None
    with open("credentials.txt", "r") as f:
        api_key = f.read()
    data = {}

    with open(file, 'r') as f:
        data = json.load(f)
    playlists = list(data.values())
    data = bidict(data)

    query_url = 'https://www.googleapis.com/youtube/v3/playlists?part=contentDetails&id={}&key={}'.format(
        ','.join(playlists), api_key)
    inp = urllib.request.urlopen(query_url)
    resp = json.load(inp)

    count = {}
    for i in resp['items']:
        zone = data.inverse[i['id']][0]
        count[zone] = i['contentDetails']['itemCount']
    print(count)
    return count


def generate_area_popup_html(area_name, redirect, placeholder):
    """
    Generate the html code tat shows the sector name and the link to the playlist
    when clicking on the sector area
    """
    return '<p><a href="'+'/'+redirect+'"target="_blank">'+area_name+r'</a><br></p><p>Beta Videos: '+placeholder+'</p>'
