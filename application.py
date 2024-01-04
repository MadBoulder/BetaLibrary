import json
import os
import random
import io
import threading
from flask import Flask, render_template, send_from_directory, request, abort, session, redirect, url_for, send_file, jsonify
from flask_caching import Cache
from flask_babel import Babel, _
from flask_mail import Mail,  Message
from urllib.parse import urlparse
from jinja2 import Environment, FileSystemLoader
import datetime
import utils.helpers
import utils.js_helpers
import utils.zone_helpers
import dashboard
import dashboard_videos
import handle_channel_data
import re
import time
from slugify import slugify

from bokeh.embed import components
from bokeh.resources import INLINE
import mailerlite as MailerLite

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account


EXTENSION = '.html'
NUM_RESULTS = 4
EMAIL_SUBJECT_FIELDS = ['name', 'zone', 'climber']
REMOVE_FIRST = slice(1, None, 1)
MAILERLITE_API_KEY = os.environ['MAILERLITE_API_KEY']

# create and configure the application object
app = Flask(__name__, static_folder='static')
app.config.from_pyfile('config.py')
app.secret_key = b'\xf7\x81Q\x89}\x02\xff\x98<et^'
babel = Babel(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


current_progress = 0


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


@cache.cached(
    timeout=_get_seconds_to_next_time(hour=11, minute=10, second=00),
    key_prefix='mad_zones'
)
def get_zone_data():
    return handle_channel_data.get_zone_data()
def get_playlist_data():
    return handle_channel_data.get_playlist_data()

# Set language
@app.route('/language/<language>')
def set_language(language=None):
    print("set_language")
    session['language'] = language
    referrer_url = request.referrer
    if referrer_url:
        parsed_url = urlparse(referrer_url)
        return redirect(parsed_url.path)
    else:
        return redirect('')

#@babel.localeselector
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
babel.init_app(app, locale_selector=get_locale)

@app.context_processor
def inject_language():
    language = get_locale()
    return dict(current_lang=language)


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
@app.route('/home.html')
@app.route('/home')
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/bouldering-areas-list', methods=['GET', 'POST'])
def zones():
    # TODO: POST and GET methods are handled equally
    # if request.method == 'GET':
    # if request.method == 'POST':
    # each zone has: link, name, num.videos
    zones = get_zone_data()
    playlists = get_playlist_data()
    country_data = handle_channel_data.get_country_data()
    return render_template(
        'bouldering-areas-list.html',
        zones=zones['items'],
        playlists=playlists['items'],
        countries=app.config['COUNTRIES'],
        country_data=country_data['items'])


@app.route('/area-problem-finder', methods=['GET', 'POST'])
def search():
    query = ""
    search_results = {}
    
    if request.method == 'POST':
        query = request.form.get('searchterm', '')
        if not query:
            query = request.form.get('searchterm-small', '')
        return redirect(url_for('search', search_query=query))
    elif request.method == 'GET':
        query = request.args.get('search_query', '')
        
    print(f"Search request: {query}")
    if query:
        start_time = time.time()
        threads = []

        def search_zone():
            search_zone_start_time = time.time()
            search_results['zones'] = utils.helpers.search_zone(
                query, NUM_RESULTS, exact_match=True)
            search_zone_elapsed_time = time.time() - search_zone_start_time
            print(f"Search Zone execution time: {search_zone_elapsed_time} seconds")

        def search_sector():
            search_sector_start_time = time.time()
            search_results['sectors'] = utils.helpers.search_sector(
                query, NUM_RESULTS, exact_match=True)
            search_sector_elapsed_time = time.time() - search_sector_start_time
            print(f"Search Sector execution time: {search_sector_elapsed_time} seconds")

        def search_problem():
            search_problem_start_time = time.time()
            search_results['problems'] = utils.helpers.search_problem(
                query, NUM_RESULTS, exact_match=True)
            search_problem_elapsed_time = time.time() - search_problem_start_time
            print(f"Search Problem execution time: {search_problem_elapsed_time} seconds")

        def search_beta():
            search_beta_start_time = time.time()
            search_results['videos'] = utils.helpers.get_video_from_channel(
                query, results=5)
            search_beta_elapsed_time = time.time() - search_beta_start_time
            print(f"Search Beta execution time: {search_beta_elapsed_time} seconds")

        # Create and start threads for each search operation
        search_zone_thread = threading.Thread(target=search_zone)
        search_sector_thread = threading.Thread(target=search_sector)
        search_problem_thread = threading.Thread(target=search_problem)
        search_beta_thread = threading.Thread(target=search_beta)

        threads.extend([search_zone_thread, search_sector_thread, search_problem_thread, search_beta_thread])

        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        total_elapsed_time = time.time() - start_time
        print(f"Search execution time: {total_elapsed_time} seconds")
        
        return render_template(
            'area-problem-finder.html',
            zones=search_results.get('zones', []),
            sectors=search_results.get('sectors', []),
            problems=search_results.get('problems', []),
            videos=search_results.get('videos', []),
            search_term=query
        )
    return render_template(
        'area-problem-finder.html',
        zones=[],
        videos=[],
        search_term='')



@app.route('/video-uploader-not-working', methods=['GET', 'POST'])
def video_uploader_not_working():
    return render_template('video-uploader-not-working.html')
    
@app.route('/upload', methods=['GET', 'POST'])
@app.route('/video-uploader', methods=['GET', 'POST'])
def video_uploader():
    return render_template('video-uploader.html')
    
    
@app.route('/video-uploader-test', methods=['GET', 'POST'])
def video_uploader_test():
    return render_template('video-uploader.html')
    
@app.route('/upload-file', methods=['GET', 'POST'])
def upload_file():
    uploaded_file = request.files['file']

    if uploaded_file:
        try:
            upload_to_google_drive(uploaded_file)

            permissionNewsletter = request.form.get('permission-newsletter')
            if permissionNewsletter:
                email = request.form['email']
                if email:
                    register_new_subscriber(email)
            
            msg_body = 'Climber: {}\nEmail: {}\nName: {}\nGrade: {}\nZone: {}\nSector: {}\nNotes: {}\nFilename: {}\n'.format(
                request.form['climber'],
                request.form['email'],
                request.form['name'],
                request.form['grade'],
                request.form['zone'],
                request.form['sector'],
                request.form['notes'],
                uploaded_file.filename)
                
            msg = Message(
                subject='MadBoulder New Video Beta Received',
                sender=app.config.get('MAIL_USERNAME'),
                recipients=app.config.get('FEEDBACK_MAIL_RECIPIENTS'),
                body=msg_body)
            mail.send(msg)
            return jsonify({"message": "File uploaded and processed successfully"}), 200
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            return jsonify({"error": "Internal server error occurred"}), 500
    else:
        return jsonify({"error": "File upload failed. Please check your request."}), 400


def upload_to_google_drive(file):
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive']
        SERVICE_ACCOUNT_FILE = 'madboulder-file-uploader-5b2b9d6798b5.env'
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=credentials)
        if drive_service:
            CUSTOM_FOLDER_ID = '1OSocLiJSYTjVJHH_kv0umNFgTZ_G5wBB'
            file_metadata = {'name': file.filename,
                             'parents': [CUSTOM_FOLDER_ID]}
                             
            video_content = file.read()
            media = MediaIoBaseUpload(io.BytesIO(video_content), mimetype='video/mp4', chunksize=1024*1024, resumable=True)
            
            request = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
                        
            response = None
            global current_progress
            current_progress = 0
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print("Uploaded %d%%." % int(status.progress() * 100))
                    current_progress = status.progress() * 100
            current_progress = 100

            print("Upload of {} is complete.".format(file.filename))
        else:
            raise Exception("Upload failed: Couldn't create Drive service")
    except Exception as e:
        raise Exception(e)
        
        
def empty_google_drive():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = 'madboulder-file-uploader-5b2b9d6798b5.env'
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)
    # Get the list of all files in Google Drive
    file_list = drive_service.files().list(q="'root' in parents and trashed=false").execute().get('files', [])

    # Delete each file
    for file in file_list:
        drive_service.files().delete(fileId=file['id']).execute()

    # Empty the trash
    drive_service.files().emptyTrash().execute()


def register_new_subscriber(email):
    mailerlite = MailerLite.Client({
    'api_key': MAILERLITE_API_KEY
    })

    try:
        existing_subscriber = mailerlite.subscribers.get_subscriber_by_email(email)
    except:
        existing_subscriber = None

    if not existing_subscriber:
        mailerlite.subscribers.create(email=email)
        print("new email subscribed")




@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify({'progress': current_progress})

    
@app.route('/upload-completed', methods=['GET'])
def upload_completed():
    return render_template('thanks-for-uploading.html')
    

@app.route('/<string:sitemap_name>.xml')
def sitemap_file(sitemap_name):
    if re.match(r'sitemap(-\w+)?', sitemap_name):
        print(sitemap_name)
        sitemap_filename = f'{sitemap_name}.xml'   
        return send_file(sitemap_filename, mimetype='application/xml')
    else:
        return "Invalid sitemap name"
    

@app.route('/random', methods=['GET', 'POST'])
def random_zone():
    if request.method == 'GET':
        zones = next(os.walk('data/zones/'))[1]
        all_zones = ['zones/' + area for area in zones]
        return render_template(random.choice(all_zones) + EXTENSION)


@app.route('/latest-news-and-videos')
def render_latest():
    return render_template('latest-news-and-videos.html', video_urls=get_videos_from_channel())


@app.route('/bouldering-areas-map')
@app.route('/map')
def render_map():
    return render_template('bouldering-areas-map.html')


@app.route('/about-us', methods=['GET', 'POST'])
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
            return render_template('thanks-for-joining.html')
        except:
            abort(404)
            
    zone_data = handle_channel_data.get_zone_data()
    stats_list = [
        {
            'text': _('Zones'),
            'data': len(zone_data['items'])
        },
        {
            'text': _('Contributors'),
            'data': handle_channel_data.get_contributors_count()
        },
        {
            'text': _('Videos'),
            'data': 7.977
            #channel_info['items'][0]['statistics']['videoCount']
        }
    ]
    return render_template('about-us.html', stats_list=stats_list)
    
@app.route('/join-us', methods=['GET', 'POST'])
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
            return render_template('thanks-for-joining.html')
        except:
            abort(404)
    return render_template('join-us.html')


@app.route('/madboulder-terms-of-use-and-conditions')
def terms_conditions():
    return render_template('policy/madboulder-terms-of-use-and-conditions.html')
    
@app.route('/madboulder-privacy-policy')
def privacy_policy():
    return render_template('policy/madboulder-privacy-policy.html')
    
@app.route('/madboulder-cookie-policy')
def cookies():
    return render_template('policy/madboulder-cookie-policy.html')


@app.route('/bouldering')
def bouldering():
    return render_template('bouldering.html')


@app.route('/subscribe')
def subscribe():
    return render_template('subscribe.html')


@app.route('/subscription-confirmed')
def subscription_confirmed():
    return render_template('subscription-confirmed.html')
    

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
@app.route('/templates/zones/<string:page>.html')
@app.route('/<string:page>.html')
def render_page(page):
    try:
        try:
            views_count = utils.zone_helpers.get_zone_view_count_from_zone_code(slugify(page))
            video_count = get_zone_video_count(slugify(page))
            sector_count = utils.helpers.count_sectors_in_zone(page)
            data = [
                {
                    'logo': 'fas fa-video-camera',
                    'text': _('Videos'),
                    'data': video_count
                },
                {
                    'logo': 'fas fa-eye',
                    'text': _('Views'),
                    'data': views_count
                },
                {
                    'logo': 'fa fa-map-marked',
                    'text': _('Sectors'),
                    'data': sector_count
                }]
        except:
            data = []
        return render_template('zones/' + slugify(page) + EXTENSION, current_url=page, stats_list=data)
    except:
        abort(404)
        

@app.route('/problems/<string:page>/<string:problem_name>')
@app.route('/templates/problems/<string:page>/<string:problem_name>.html')
@app.route('/problems/<string:page>/<string:problem_name>.html')
@app.route('/<string:page>/problem/<string:problem_name>') #deprecated
def load_problem(page, problem_name):
    return render_template(f'problems/{slugify(page)}/{slugify(problem_name)}.html')
    
    
@app.route('/sectors/<string:page>/<string:sector_name>')
@app.route('/templates/sectors/<string:page>/<string:sector_name>.html')
@app.route('/sectors/<string:page>/<string:sector_name>.html')
@app.route('/<string:page>/sector/<string:sector_name>') #deprecated
def load_sector(page, sector_name):
    return render_template(f'sectors/{slugify(page)}/{slugify(sector_name)}.html')


@app.route('/countries/<string:country_name>')
@app.route('/templates/countries/<string:country_name>.html')
def load_country(country_name):
    return render_template(f'countries/{slugify(country_name)}.html')


@app.route('/states/<string:state_name>')
@app.route('/templates/states/<string:state_name>.html')
def load_state(state_name):
    return render_template(f'states/{slugify(state_name)}.html')


# this route is used for rendering maps inside an iframe
@app.route('/maps/<string:area>')
@app.route('/maps/<string:area>.html')
@app.route('/templates/maps/<string:area>.html')
def render_area(area):
    try:
        return render_template('maps/' + area + EXTENSION)
    except:
        abort(404)


@app.route('/download/<string:path>/<string:filename>')
def download_file(path=None, filename=None):
    try:
        download_path = os.path.join(app.root_path, 'data/zones/' + path) + '/' + filename
        return send_file(download_path, as_attachment=False)
    except:
        abort(404)


@app.errorhandler(404)
def page_not_found(error):
    app.logger.error('Page not found: %s', (request.path))
    return render_template('errors/404-page-not-found.html'), 404


# start the server
if __name__ == '__main__':
    app.run(debug=False)
