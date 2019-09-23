import os
import random
from flask import Flask, render_template, send_from_directory, request, abort
from flask_caching import Cache
from jinja2 import Environment, FileSystemLoader, select_autoescape
import helpers


EXTENSION = '.html'
NUM_RESULTS = 4

# create the application object
app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Load favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/images/logo'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# use decorators to link the function to a url
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['area']
        # Do search
        search_results = helpers.search_zone(query, NUM_RESULTS)
        print(search_results)
        # return render_template('search_results.html', search_results=results)


@app.route('/random', methods=['GET', 'POST'])
def random_zone():
    if request.method == 'GET':
        zones = next(os.walk('data/zones/'))[1]
        all_zones = ['zones/' + area for area in zones]
        return render_template(random.choice(all_zones) + EXTENSION)


@app.route('/latest_videos')
@cache.cached(timeout=900)
def render_latest():
    return render_template('latest_videos.html', video_urls=helpers.get_videos_from_channel())


@app.route('/all')
@cache.cached(timeout=60*60*24)
def render_all():
    # Since the map is rendered in an iframe inside
    # the main html of the page, jinja template variables
    # that are inside the map are not replaced by default
    # if we pass data to render_template. This is why we
    # first load the maps/all template, replace the variables
    # iniside the html by the data obtained at runtime,
    # and finally render the page template
    template_loader = FileSystemLoader(searchpath=".")
    template_env = Environment(loader=template_loader)
    data = helpers.get_number_of_videos_from_playlists_file(
        'data/playlist.txt')
    template = template_env.get_template('templates/maps/all.html')
    # Here we replace zone_name in maps/all by the number of beta videos
    output = template.render(**data)
    with open('templates/maps/all.html', 'w') as template:
        template.write(output)
    # After the data has been replaced, render the template
    return render_template('all.html')


@app.route('/about_us')
def render_about_us():
    return render_template('about_us.html')


@app.route('/<string:page>')
def render_page(page):
    try:
        return render_template('zones/' + page + EXTENSION)
    except:
        abort(404)

# this route is used for rendering maps inside an iframe
@app.route('/maps/<string:area>')
def render_area(area):
    try:
        return render_template('maps/' + area + EXTENSION)
    except:
        abort(404)


@app.errorhandler(404)
def page_not_found(error):
    app.logger.error('Page not found: %s', (request.path))
    return render_template('errors/404.html'), 404


# start the server
if __name__ == '__main__':
    app.run(debug=False)
