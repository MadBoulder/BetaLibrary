import os
from flask import Flask, render_template, send_from_directory, request
from flask_caching import Cache
import helpers

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
        return render_template(query + ".html")


@app.route('/latest_videos')
@cache.cached(timeout=60)
def render_latest():
    return render_template('latest_videos.html', video_urls=helpers.get_videos_from_channel())


@app.route('/<string:page>')
def render_page(page):
    return render_template(page + ".html")

# this route is used for rendering maps inside an iframe
@app.route('/maps/<string:area>')
def render_area(area):
    return render_template('maps/' + area + ".html")


# start the server
if __name__ == '__main__':
    app.run(debug=False)
