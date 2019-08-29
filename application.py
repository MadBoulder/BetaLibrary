import os
from flask import Flask, render_template, send_from_directory, request
from flask_caching import Cache
from jinja2 import Environment, FileSystemLoader, select_autoescape
import helpers

EXTENSION = '.html'

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
        return render_template(query + EXTENSION)


@app.route('/latest_videos')
@cache.cached(timeout=900)
def render_latest():
    return render_template('latest_videos.html', video_urls=helpers.get_videos_from_channel())


@app.route('/all')
@cache.cached(timeout=60*60*24)
def render_all():
    template_loader = FileSystemLoader(searchpath=".")
    template_env = Environment(loader=template_loader)
    data = helpers.get_number_of_videos_from_playlists_file(
        'data/playlist.txt')
    template = template_env.get_template('templates/maps/all.html')
    output = template.render(**data)
    with open('templates/maps/all.html', 'w') as template:
        template.write(output)
    return render_template('all.html')


@app.route('/about_us')
def render_about_us():
    return render_template('about_us.html')


@app.route('/<string:page>')
def render_page(page):
    return render_template('zones/' + page + EXTENSION)

# this route is used for rendering maps inside an iframe
@app.route('/maps/<string:area>')
def render_area(area):
    return render_template('maps/' + area + EXTENSION)


# start the server
if __name__ == '__main__':
    app.run(debug=False)
