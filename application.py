import json
import os
import random
from flask import Flask, render_template, send_from_directory, request, abort, session, redirect
from flask_caching import Cache
from flask_babel import Babel, _
from flask_mail import Mail,  Message
from urllib.parse import urlparse
from jinja2 import Environment, FileSystemLoader
import datetime
import utils.helpers
import utils.js_helpers
import dashboard
import dashboard_videos
import handle_channel_data

from bokeh.embed import components
from bokeh.resources import INLINE


EXTENSION = '.html'
NUM_RESULTS = 4
EMAIL_SUBJECT_FIELDS = ['name', 'zone', 'climber']
REMOVE_FIRST = slice(1, None, 1)

# create and configure the application object
app = Flask(__name__, static_folder='static')
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


def _get_seconds_to_next_time(hour=11, minute=10, second=0):
    now = datetime.datetime.now()
    if now.hour >= hour and now.minute > minute:
        wait_seconds = 24*60*60 - ((now.hour - hour)*60*60 + minute*60)
    else:
        next_time = now.replace(hour=hour, minute=minute, second=second)
        wait_seconds = (next_time - now).seconds
    return wait_seconds

# Cached functions
@cache.cached(timeout=900, key_prefix='videos_from_channel')
def get_videos_from_channel():
    return utils.helpers.get_videos_from_channel()


@cache.memoize(timeout=3600)
def get_zone_video_count(page):
    return utils.helpers.get_number_of_videos_for_zone(page)


@cache.cached(timeout=60*60*24, key_prefix='map_all')
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
    data = utils.helpers.get_number_of_videos_from_playlists_file()
    # store num videos in session to avoid repeating calls
    session['video_count'] = data
    template = template_env.get_template('templates/maps/all_to_render.html')
    # Here we replace zone_name in maps/all by the number of beta videos
    output = template.render(**data)
    output = utils.js_helpers.replace_sectors_placeholders_for_translations(
        output)
    with open('templates/maps/all.html', 'w', encoding='utf-8') as template:
        template.write(output)


@cache.cached(
    timeout=_get_seconds_to_next_time(hour=11, minute=10, second=00),
    key_prefix='mad_zones'
)
def get_zone_data():
    return handle_channel_data.get_zone_data()

# Set language
@app.route('/language/<language>')
def set_language(language=None):
    session['language'] = language
    referrer_url = request.referrer
    if referrer_url:
        parsed_url = urlparse(referrer_url)
        page_name = parsed_url.path.split('/')[-1]
        
        args = '&'.join(['{}={}'.format(str(key), str(value))
            for key, value in request.args.items()])
        return redirect('/{}?{}'.format(page_name, args))
    else:
        return redirect('')

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

# robots
@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

# cache keys for zones
def zone_cache_key():
    return request.url

# use decorators to link the function to a url
@app.route('/')
def home():
    channel_info = utils.helpers.get_channel_info()
    zones = utils.helpers.load_zones()
    stats_list = [
        {
            'logo': 'fa fa-globe-americas',
            'text': _('Zones'),
            'data': len(zones)
        },
        {
            'logo': 'fa fa-users',
            'text': _('Contributors'),
            'data': handle_channel_data.get_contributors_count()
        },
        {
            'logo': 'fab fa-youtube',
            'text': _('Videos'),
            'data': channel_info['items'][0]['statistics']['videoCount']
        },
        {
            'logo': 'fa fa-eye',
            'text': _('Views'),
            'data': channel_info['items'][0]['statistics']['viewCount']
        }
    ]
    return render_template('home.html', stats_list=stats_list)

@app.route('/home2')
def home2():
    return render_template('home2.html')

@app.route('/zones', methods=['GET', 'POST'])
def zones():
    with open('data/countries.json', 'r') as c_data:
        country_data = json.load(c_data)
    # TODO: POST and GET methods are handled equally
    # if request.method == 'GET':
    # if request.method == 'POST':
    # each zone has: link, name, num.videos
    zones = get_zone_data()
    return render_template(
        'zones.html',
        zones=zones['items'],
        countries=app.config['COUNTRIES'],
        country_data=country_data,
        current_lang=get_locale())


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('searchterm', '')
        if not query:
            query = request.form.get('searchterm-small', '')
        # Search zones and betas
        search_zone_results = utils.helpers.search_zone(
            query, NUM_RESULTS, exact_match=True)
        search_beta_results = utils.helpers.get_video_from_channel(
            query, results=5)
        return render_template(
            'search_results.html',
            zones=search_zone_results,
            videos=search_beta_results,
            search_term=query
        )
    if request.method == 'GET':
        query = request.args.get('search_query', '')
        if query:
            search_zone_results = utils.helpers.search_zone(
                query, NUM_RESULTS, exact_match=True)
            search_beta_results = utils.helpers.get_video_from_channel(
                query, results=5)
            return render_template(
                'search_results.html',
                zones=search_zone_results,
                videos=search_beta_results,
                search_term=query
            )
        return render_template(
            'search_results.html',
            zones=[],
            videos=[],
            search_term='')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    # return render_template('upload_not_working.html')
    return render_template('upload.html')


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
        try:
            # build email text/body
            feedback_data = request.form['feedback']
            sender_email = request.form['email']
            msg_body = 'Sender: {}\nMessage: {}'.format(
                sender_email, feedback_data)
            # build email
            msg = Message(
                subject='madboulder.org feedback',
                sender=app.config.get('MAIL_USERNAME'),
                recipients=app.config.get('FEEDBACK_MAIL_RECIPIENTS'),
                body=msg_body)
            mail.send(msg)
            return render_template('thanks_for_joining.html')
        except:
            abort(404)
    return render_template('about_us.html')
    
@app.route('/join_us', methods=['GET', 'POST'])
def join_us():
    if request.method == 'POST':
        try:
            sender_name = request.form['name']
            sender_message = request.form['message']
            sender_email = request.form['email']
            resume = request.files['resume']
            msg_body = 'Sender: {} - {}\nMessage: {}'.format(
                sender_name, sender_email, sender_message)
                
            msg = Message(
                subject='madboulder.org join us',
                sender=app.config.get('MAIL_USERNAME'),
                recipients=app.config.get('FEEDBACK_MAIL_RECIPIENTS'),
                body=msg_body)
            msg.attach(resume.filename, 'application/octet-stream', resume.read())
            mail.send(msg)
            return render_template('thanks_for_joining.html')
        except:
            abort(404)
    return render_template('join_us.html')

@app.route('/disclosure')
def affiliate_disclosure():
    return render_template('policy/affiliate_disclosure_deprecated.html')


@app.route('/terms_conditions')
def terms_conditions():
    return render_template('policy/terms_conditions.html')
    
@app.route('/privacy_policy')
def privacy_policy():
    return render_template('policy/privacy_policy.html')
    
@app.route('/cookies')
def cookies():
    return render_template('policy/cookies.html')

# Cache until
@app.route('/statistics')
@cache.cached(
    timeout=_get_seconds_to_next_time(hour=11, minute=10, second=00),
    key_prefix='mad_statistics'
)
def statistics():
    layout = dashboard.get_dashboard()
    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    # render template
    script, div = components(layout)
    return render_template(
        'dashboard.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
        last_update=dashboard.get_last_dashboard_update()
    )


@app.route('/video_statistics')
@cache.cached(
    timeout=_get_seconds_to_next_time(hour=11, minute=10, second=00),
    key_prefix='mad_custom_statistics'
)
def custom_statistics():
    layout = dashboard_videos.get_dashboard()
    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    # render template
    script, div = components(layout)
    return render_template(
        'dashboard_videos.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
        last_update=dashboard.get_last_dashboard_update()
    )

# video count is cached for one hour
@app.route('/<string:page>')
def render_page(page):
    try:
        video_count = get_zone_video_count(page)
        data = [
            #{
            #    'logo': 'fa fa-map-marked',
            #    'text': _('Sectors'),
            #    'data': utils.helpers.count_sectors_in_zone(page)
            #},
            {
                'logo': 'fab fa-youtube',
                'text': _('Videos'),
                'data': video_count
            }]
        return render_template('zones/' + page + EXTENSION, current_url=page, stats_list=data, lang=get_locale())
    except:
        abort(404)

@app.route('/<string:page>/problem/<string:problem_name>')
def load_problem(page, problem_name):
    return render_template(f'problems/{page}/{problem_name}.html')
    
@app.route('/<string:page>/sector/<string:sector_name>')
def load_sector(page, sector_name):
    return render_template(f'sectors/{page}/{sector_name}.html')

# this route is used for rendering maps inside an iframe
@app.route('/maps/<string:area>')
def render_area(area):
    try:
        return render_template('maps/' + area + EXTENSION)
    except:
        abort(404)


@app.route('/download/<string:path>/<string:filename>')
def download_file(path=None, filename=None):
    try:
        download_path = os.path.join(app.root_path, 'data/zones/' + path)
        return send_from_directory(
            directory=download_path,
            filename=filename,
            as_attachment=False
        )
    except:
        abort(404)


@app.errorhandler(404)
def page_not_found(error):
    app.logger.error('Page not found: %s', (request.path))
    return render_template('errors/404.html'), 404


# start the server
if __name__ == '__main__':
    app.run(debug=False)
