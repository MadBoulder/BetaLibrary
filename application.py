import os
import random
from flask import Flask, render_template, send_from_directory, request, abort, session, redirect, url_for
from flask_caching import Cache
from flask_babel import Babel, _
from flask_mail import Mail,  Message
from jinja2 import Environment, FileSystemLoader, select_autoescape
import helpers
import js_helpers
from werkzeug.utils import secure_filename


EXTENSION = '.html'
NUM_RESULTS = 4
EMAIL_SUBJECT_FIELDS = ['name', 'zone', 'climber']

# create the application object
app = Flask(__name__)
app.config.from_pyfile('config.py')
app.secret_key = b'\xf7\x81Q\x89}\x02\xff\x98<et^'
babel = Babel(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.environ['EMAIL_USER'],
    "MAIL_PASSWORD": os.environ['EMAIL_PASSWORD'],
    "MAIL_RECIPIENTS": os.environ['EMAIL_RECIPIENTS'].split(":"),
    "FEEDBACK_MAIL_RECIPIENTS": os.environ['FEEDBACK_MAIL_RECIPIENTS'].split(":")
}

app.config.update(mail_settings)
mail = Mail(app)

# Cached functions
@cache.cached(timeout=900, key_prefix='videos_from_channel')
def get_videos_from_channel():
    return helpers.get_videos_from_channel()


@cache.cached(timeout=60*60*24, key_prefix="map_all")
def get_map_all():
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
    # store num videos in session to avoid repeating calls
    session['video_count'] = data
    template = template_env.get_template('templates/maps/all_to_render.html')
    # Here we replace zone_name in maps/all by the number of beta videos
    output = template.render(**data)
    output = js_helpers.replace_sectors_placeholders_for_translations(
        output)
    with open('templates/maps/all.html', 'w', encoding="utf-8") as template:
        template.write(output)


# Set language
@app.route('/language/<language>')
def set_language(language=None):
    session['language'] = language
    args = '&'.join(['{}={}'.format(str(key), str(value))
                     for key, value in request.args.items() if key != 'origin'])
    return redirect('/{}?{}'.format(request.args.get('origin', ''), args))


@babel.localeselector
def get_locale():
    # if the user has set up the language manually it will be stored in the session,
    # so we use the locale from the user settings
    try:
        language = session['language']
    except KeyError:
        language = request.accept_languages.best_match(app.config['LANGUAGES'])
    if language is not None:
        return language
    return 'en'


# Load favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/images/logo'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# cache keys for zones
def zone_cache_key():
    return request.url

# use decorators to link the function to a url
@app.route('/')
def home():
    channel_info = helpers.get_channel_info()
    zones = helpers.load_zones()
    stats_list = [
        {
            'logo': "fa fa-globe-americas",
            'text': _("Zones"),
            'data': len(zones)
        },
        {
            'logo': "fa fa-map-marked",
            'text': _("Sectors"),
            'data': sum([helpers.count_sectors_in_zone(zone['file']) for zone in zones])
        },
        {
            'logo': "fab fa-youtube",
            'text': _("Videos"),
            'data': channel_info['items'][0]['statistics']['videoCount']
        },
        {
            'logo': "fa fa-eye",
            'text': _("Views"),
            'data': channel_info['items'][0]['statistics']['viewCount']
        }
    ]
    return render_template('home.html', stats_list=stats_list)


@app.route('/zones')
def zones():
    return render_template('zones.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['area']
        # Do search
        search_results = helpers.search_zone(query, NUM_RESULTS)
        return render_template('search_results.html', zones=search_results, search_term=query)
    if request.method == 'GET':
        query = request.args.get('search_query', '')
        # Do search
        if query:
            search_results = helpers.search_zone(query, NUM_RESULTS)
            return render_template('search_results.html', zones=search_results, search_term=query)
        return render_template('search_results.html', zones=[], search_term='')


@app.route('/search_beta', methods=['GET', 'POST'])
def search_beta():
    if request.method == 'POST':
        query = request.form['beta']
        # Do search
        search_results = helpers.get_video_from_channel(query)
        return render_template(
            'search_beta_results.html',
            videos=search_results,
            search_term=query
        )
    if request.method == 'GET':
        query = request.args.get('search_query', '')
        # Do search
        if query:
            search_results = helpers.get_video_from_channel(query)
            return render_template(
                'search_beta_results.html',
                videos=search_results,
                search_term=query
            )
        return render_template(
            'search_beta_results.html',
            videos=[],
            search_term=''
        )


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    upload_complete = False
    if request.method == 'POST':
        # build email text/body
        video_data = ("\n").join(["{}: {}".format(key, value)
                                  for key, value in request.form.items()])
        video_data = video_data.replace('wt_embed_output', 'download link')
        # build email
        msg = Message(
            subject=(", ").join([request.form[field]
                                 for field in EMAIL_SUBJECT_FIELDS]),
            sender=app.config.get("MAIL_USERNAME"),
            recipients=app.config.get("MAIL_RECIPIENTS"),
            body=video_data)
        mail.send(msg)
        # If no errors are raised, assume the action was successful
        upload_complete = True
    return render_template(
        'upload.html',
        locale=app.config["WE_TRANSFER_LOCALE_MAPPING"][get_locale()],
        success=upload_complete,
        wt_key=os.environ["WT_KEY"]
    )


@app.route('/random', methods=['GET', 'POST'])
def random_zone():
    if request.method == 'GET':
        zones = next(os.walk('data/zones/'))[1]
        all_zones = ['zones/' + area for area in zones]
        return render_template(random.choice(all_zones) + EXTENSION)


@app.route('/latest_videos')
def render_latest():
    return render_template('latest_videos.html', video_urls=get_videos_from_channel())


@app.route('/all')
def render_all():
    get_map_all()
    # After the data has been replaced, render the template
    return render_template('all.html')


@app.route('/about_us', methods=['GET', 'POST'])
def render_about_us():
    if request.method == 'POST':
        # build email text/body
        feedback_data = request.form['feedback']
        # build email
        print(feedback_data)
        msg = Message(
            subject='madboulder.org feedback',
            sender=app.config.get("MAIL_USERNAME"),
            recipients=app.config.get("FEEDBACK_MAIL_RECIPIENTS"),
            body=feedback_data)
        mail.send(msg)
        # If no errors are raised, assume the action was successful
    return render_template('about_us.html')

# cache page results for one hour
@app.route('/<string:page>')
@cache.cached(timeout=3600, key_prefix=zone_cache_key)
def render_page(page):
    try:
        video_count = session['video_count'][page]
    except:
        # if cache has expired and the session does not contain the data,
        # compute it again and store it. Worst case scenario,
        # number of videos will be updated once a day
        video_count = helpers.get_number_of_videos_for_zone(page)
        if session.get('video_count', None) is not None:
            session['video_count'][page] = video_count
        else:
            session['video_count'] = {page: video_count}
    data = [
    {
        'logo': "fab fa-youtube",
        'text': _("Videos"),
        'data': video_count
    }]
    try:
        return render_template('zones/' + page + EXTENSION, current_url=page, stats_list=data)
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
