import json
import os
import uuid
import random
import io
import threading
from flask import Flask, render_template, send_from_directory, request, abort, session, redirect, url_for, send_file, jsonify
from flask_caching import Cache
from flask_babel import Babel, _
import firebase_admin
from firebase_admin import credentials, auth, db, exceptions
from firebase_admin.exceptions import FirebaseError
from urllib.parse import urlparse
from datetime import datetime, timedelta
from utils.emailProvider import EmailProvider
import utils.helpers
import utils.js_helpers
import utils.zone_helpers
import utils.MadBoulderDatabase
import utils.channel
import utils.drive
import dashboard
import dashboard_videos
import re
import time
from slugify import slugify
from functools import wraps
from dotenv import load_dotenv
import traceback
import requests
import utils.searchManager
from types import SimpleNamespace

from bokeh.embed import components
from bokeh.resources import INLINE
import mailerlite as MailerLite

from google.oauth2 import service_account

from google.cloud import recaptchaenterprise_v1
from google.cloud.recaptchaenterprise_v1 import Assessment

from werkzeug.utils import secure_filename
from pathlib import Path
import utils.channel_uploader as channel_uploader

EXTENSION = '.html'
EMAIL_SUBJECT_FIELDS = ['name', 'zone', 'climber']
REMOVE_FIRST = slice(1, None, 1)

load_dotenv()  # Take environment variables from .env.  

# create and configure the application object
app = Flask(__name__, static_folder='static')
app.config.from_pyfile('config.py')
app.config['UPLOAD_FOLDER'] = '/tmp'  # or another appropriate temporary directory
app.config['LOCAL_VIDEOS_FOLDER'] = os.getenv('LOCAL_VIDEOS_FOLDER')
app.config['UPLOADED_VIDEOS_FOLDER'] = os.getenv('UPLOADED_VIDEOS_FOLDER')
if os.environ.get('FLASK_ENV') == 'production':
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
app.secret_key = bytes.fromhex(os.environ.get('SECRET_KEY'))
app.jinja_env.filters['format_views'] = utils.helpers.format_views
babel = Babel(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
cred = credentials.Certificate('madboulder.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://madboulder.firebaseio.com'
})
mailerlite = MailerLite.Client({
    'api_key': os.environ['MAILERLITE_API_KEY']
})

SERVICE_ACCOUNT_FILE = 'madboulder-f1887f0310ec.env'
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
recaptcha_client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient(credentials=credentials)


current_progress = 0

mail = EmailProvider(app)

search_manager = utils.searchManager.SearchManager()

def _get_seconds_to_next_time(hour, minute, second):
    """Get seconds until next occurrence of the specified time"""
    now = datetime.now()
    next_time = now.replace(hour=hour, minute=minute, second=second)
    
    if next_time <= now:
        next_time += timedelta(days=1)
        
    return (next_time - now).total_seconds()


@cache.cached(
    timeout=_get_seconds_to_next_time(hour=11, minute=10, second=00),
    key_prefix='mad_zones'
)
def get_zone_data():
    return utils.MadBoulderDatabase.getAreasData()
def get_playlist_data():
    return utils.MadBoulderDatabase.getPlaylistsData()

# Set language
@app.route('/language/<language>')
def set_language(language=None):
    print("set_language")
    session['language'] = language
    referrer_url = request.referrer
    print("referrer_url: " + referrer_url)
    if referrer_url:
        parsed_url = urlparse(referrer_url)
        print("parsed_url.path: " + parsed_url.path)
        path_without_language = parsed_url.path.replace('/es/', '/').replace('/en/', '/')
        return redirect(path_without_language)
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


@app.route('/ads.txt')
def ads():
    return send_file('ads.txt')

# cache keys for zones
def zone_cache_key():
    return request.url


@app.route('/home.html')
@app.route('/home')
@app.route('/')
def home():
    language_extension = ''
    if get_locale() == 'es':
        language_extension = 'es/'

    home_path = '/' + language_extension + 'home' + EXTENSION
    return render_template(home_path)


@app.route('/es/home.html')
@app.route('/es/home')
@app.route('/es')
def home_es():
    return render_template('/es/home.html')


@app.route('/bouldering-areas-list', methods=['GET'])
def zones():
    return render_template('bouldering-areas-list.html')


@app.route('/area-problem-finder', methods=['GET', 'POST'])
def search():
    query = ""
    
    if request.method == 'POST':
        query = request.form.get('searchterm', '')
        if not query:
            query = request.form.get('searchterm-small', '')
        return redirect(url_for('search', search_query=query))
    elif request.method == 'GET':
        query = request.args.get('search_query', '')
        
    print(f"Search request: {query}")
    if query:
        session_id = session.get('session_id')
        if not session_id:
            session_id = session['session_id'] = str(uuid.uuid4().hex)

        max_score = 0.01
        results = search_manager.search(session_id, query, max_score)
        return render_template(
            'area-problem-finder.html',
            areas=results.get('areas', []),
            problems=results.get('problems', []),
            search_term=query,
        )
    return render_template(
        'area-problem-finder.html', areas=[], videos=[], search_term='')


@app.route('/search-api', methods=['GET'])
def search_api():
    query = request.args.get('query', '')
    print(f"Search API request: {query}")
    if query:
        session_id = session.get('session_id')
        if not session_id:
            session_id = session['session_id'] = str(uuid.uuid4().hex)

        max_score = 0.01
        results = search_manager.search(session_id, query, max_score)
        if results:
            return jsonify({
                'areas': results.get('areas', []),
                'problems': results.get('problems', [])
            })

    return jsonify({'areas': [], 'problems': []})


@app.route('/video-uploader-not-working', methods=['GET', 'POST'])
def video_uploader_not_working():
    return render_template('video-uploader-not-working.html')


@app.route('/upload', methods=['GET', 'POST'])
@app.route('/video-uploader', methods=['GET', 'POST'])
def video_uploader():
    user_uid = session.get('uid')
    user_data = getUserData(user_uid)
    contributors = utils.MadBoulderDatabase.getContributorNames()
    climbers = contributors
    playlists = utils.MadBoulderDatabase.getPlaylistsData()
    areas = {
        playlist["zone_code"]: {
            "name": playlist["title"],
            "sectors": [
                {"name": sector["name"], "sector_code": sector_code}
                for sector_code, sector in playlist.get("sectors", {}).items()
            ],
        }
        for playlist in playlists.values()
    }
    return render_template('video-uploader.html', user_data=user_data, climbers=sorted(climbers), areas=areas)


@app.route('/video-uploader-test', methods=['GET', 'POST'])
def video_uploader_test():
    return render_template('video-uploader.html')


@app.route('/upload-file', methods=['GET', 'POST'])
def upload_file():
    print("upload_file")
    uploaded_file = request.files['file']

    if uploaded_file:
        try:
            properties_dict = {
                'name': request.form.get('name', ''),
                'email': request.form.get('email', ''),
                'grade': request.form.get('grade', ''),
                'zone': request.form.get('area', ''),
                'climber': request.form.get('climber', ''),
                'sector': request.form.get('sector', ''),
                'notes': request.form.get('notes', '')
            }
            properties = SimpleNamespace(**properties_dict)

            renamed_file = rename_file(uploaded_file.filename, properties.name, properties.grade, properties.zone)
            
            file_id = utils.drive.upload(uploaded_file, renamed_file, vars(properties))

            permissionNewsletter = request.form.get('permission-newsletter')
            if permissionNewsletter and properties.email:
                register_new_subscriber(properties.email)

            mail.sendNewVideoBeta(properties, renamed_file, file_id)

            return jsonify({"message": "File uploaded, renamed, and notification sent successfully"}), 200
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            return jsonify({"error": "Internal server error occurred"}), 500
    else:
        return jsonify({"error": "File upload failed. Please check your request."}), 400


def rename_file(original_filename, name, grade, zone):
    # name format: "Name, Grade. Zone.mp4"
    extension = original_filename.split('.')[-1]
    renamed_filename = f"{name}, {grade}. {zone}.{extension}"
    print(f"Renamed file to: {renamed_filename}")
    return renamed_filename


@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify({'progress': current_progress})


@app.route('/upload-completed', methods=['GET'])
def upload_completed():
    return render_template('thanks-for-uploading.html')


@app.route('/upload-hub')
def upload_hub():
    try:
        file_id = request.args.get('file_id')
        if file_id:
            session['file_id'] = file_id  # Save file_id in session for redirection
        else:
            file_id = session.get('file_id')  # Use stored file_id if available

        if not file_id:
            return "Error: No file ID provided.", 400

        isAuthenticated = utils.channel.is_authenticated()
        if not isAuthenticated:
            return render_template('upload-hub.html', authenticated=False, file_id=file_id)

        metadata = utils.drive.getFileMetadata(file_id)
        if not metadata:
            return "Error fetching metadata from Google Drive.", 500
        
        filename = metadata.get('name', 'Unknown File')
        title = os.path.splitext(filename)[0]

        thumbnail = metadata.get('thumbnailLink')

        properties = metadata.get('properties', {})
        climber = properties.get('climber', 'Unknown Climber')
        name = properties.get('name', 'Unknown Problem')
        grade = properties.get('grade', '')
        zone = properties.get('zone', 'Unknown Zone')
        zone_code = slugify(zone)
        sector = properties.get('sector', '')
        sector_code = slugify(sector)

        is_short = utils.helpers.isVideoShort(file_id)
        schedule_info = utils.helpers.suggestUploadTime(is_short, name, climber, grade, zone)
        description = utils.helpers.generateDescription(name, climber, grade, zone, properties.get('sector'))
        tags = utils.helpers.generateTags(name, zone, grade)

        context = {
            "authenticated": isAuthenticated,
            "file_id": file_id,
            "title": title,
            "description": description,
            "tags": ", ".join(tags),
            "thumbnail": thumbnail,
            "zone_code": zone_code,
            "sector_code": sector_code,
            "schedule_info": schedule_info,
            "is_short": is_short
        }
        return render_template('upload-hub.html', **context)

    except Exception as e:
        print(f"Error in upload_hub: {e}")
        return str(e), 500
    

@app.route('/local-upload-hub')
def local_upload_hub():
    isAuthenticated = utils.channel.is_authenticated()
    if not isAuthenticated:
        return render_template('local-upload-hub.html', authenticated=False)
    
    try:
        contributors = utils.MadBoulderDatabase.getContributorNames()
        climbers = contributors  # Direct assignment since contributors is a list of names
    except Exception as e:
        print(f"Error fetching contributor names: {e}")
        climbers = []  # Fallback to empty list if an error occurs
    
    return render_template("local-upload-hub.html", 
        authenticated=True,
        climbers=sorted(climbers)
    )


@app.route('/compute-upload-metadata', methods=['POST'])
def compute_upload_metadata():
    try:
        data = request.get_json()
        problemName = data.get('problem', 'Unknown Problem')
        grade = data.get('grade', '')
        climber = data.get('climber', 'Unknown Climber')
        zone = data.get('zone', 'Unknown Zone')
        sector = data.get('sector', '')
        is_short = data.get('is_short', False)
        
        schedule_info = utils.helpers.suggestUploadTime(is_short, climber, grade, zone)
        description = utils.helpers.generateDescription(problemName, climber, grade, zone, sector, is_short)
        tags = utils.helpers.generateTags(problemName, zone, grade)
        
        return jsonify({
             'description': description,
             'tags': ", ".join(tags),
             'schedule_info': schedule_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/test-schedule', methods=['GET'])
def test_schedule():
    """Test endpoint to check scheduling recommendation without uploading"""
    try:
        # Get parameters from the request
        is_short = request.args.get('is_short', 'false').lower() == 'true'
        climber = request.args.get('climber', 'Unknown Climber')
        grade = request.args.get('grade', '')
        zone = request.args.get('zone', 'Unknown Zone')

        # Get AI recommendation
        schedule_info = utils.helpers.suggestUploadTime(is_short, climber, grade, zone)
        if schedule_info and schedule_info.get('success'):
            publish_time = datetime.strptime(schedule_info['scheduled_time'], "%Y-%m-%d %H:%M:%S")
            return jsonify({
                'success': True,
                'scheduled_time': schedule_info['scheduled_time'],
                'hour': publish_time.hour,
                'reasoning': schedule_info.get('reasoning', '')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not determine scheduling time'
            })

    except Exception as e:
        print(f"Error testing schedule: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/authenticate')
def authenticate():
    local=request.host.startswith('localhost') or request.host.startswith('127.0.0.1')
    return utils.channel.authenticate(local)    


@app.route('/oauth2callback')
def oauth2callback():
    authorization_response=request.url
    utils.channel.oauth2callback(authorization_response)

    return redirect(url_for('upload_hub'))


@app.route('/process-upload-youtube-from-local', methods=['POST'])
def process_upload_youtube_from_local():
    try:
        # Get form data
        video_filename = request.form['video']
        description = request.form['description']
        tags = request.form['tags']
        scheduled_time = request.form.get('scheduled_time', '')
        
        # Get the full path from local videos folder
        video_path = Path(app.config['LOCAL_VIDEOS_FOLDER']) / video_filename
        
        if not video_path.exists():
            raise Exception(f"Video file not found: {video_filename}")
        
        title = os.path.splitext(video_filename)[0]

        # Extract zone and sector from description
        zone_match = re.search(r'Zone:\s*([^,\n]+)', description)
        sector_match = re.search(r'Sector:\s*([^,\n]+)', description)
        
        zone = zone_match.group(1).strip() if zone_match else "Unknown Zone"
        sector = sector_match.group(1).strip() if sector_match else ""
        
        # Generate slugified codes
        zone_code = slugify(zone)
        sector_code = slugify(sector)

        # Upload to channel
        with open(video_path, 'rb') as video_file:
            response, publish_time, error = channel_uploader.process_channel_upload(
                title=title,
                description=description,
                tags=tags,
                scheduled_time=scheduled_time,
                zone_code=zone_code,
                sector_code=sector_code,
                video_stream=video_file
            )
            
            if error:
                return error

        # Move the file to uploaded videos folder on success
        uploaded_path = Path(app.config['UPLOADED_VIDEOS_FOLDER']) / video_filename
        try:
            uploaded_path.parent.mkdir(parents=True, exist_ok=True)
            video_path.rename(uploaded_path)
        except Exception as move_error:
            print(f"Warning: Could not move file to done folder: {move_error}")
                
        return channel_uploader.generate_success_page(response['id'], title, publish_time)

    except Exception as e:
        print(f"Error in process_upload_youtube_from_local: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/process-upload-youtube-from-drive', methods=['POST'])
def process_upload_youtube_from_drive():
    try:
        if not utils.channel.is_authenticated():
            return redirect(url_for('authenticate'))
        
        file_id = session.get('file_id')
        if not file_id:
            return "Error: No file ID available.", 400
        
        title = request.form['title']
        description = request.form['description']
        tags = request.form.getlist('tags')
        zone_code = request.form['zone_code']
        sector_code = request.form['sector_code']
        scheduled_time = request.form.get('scheduled_time')
        
        video_stream = utils.drive.getVideoStream(file_id)
        print("video stream from Drive ready")
        
        response, publish_time, error = channel_uploader.process_channel_upload(
            title=title,
            description=description,
            tags=tags,
            scheduled_time=scheduled_time,
            zone_code=zone_code,
            sector_code=sector_code,
            video_stream=video_stream
        )
        
        if error:
            return error
            
        return channel_uploader.generate_success_page(response['id'], title, publish_time)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/login', methods=['GET'])
def login():
    caller_url = request.args.get('caller_url', None)
    if caller_url:
        session['nextUrl'] = caller_url
    return render_template('login.html')


@app.route('/signup', methods=['GET'])
def signup():
    return render_template('signup.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Session cleared on server."}), 200


@app.route('/verify-token', methods=['POST'])
def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization token is missing or invalid.'}), 401
    id_token = auth_header.split(' ')[1]

    try:
        uid = get_user_uid(id_token)
        session['uid'] = uid
        session['is_admin'] = check_admin_privileges(uid)

        return jsonify({"message": "Token verified", "uid": uid}), 200
    except Exception as e:
        print(f"Error verifying token: {e}")
        return jsonify({"error": str(e)}), 401
    
    
@app.route('/register-subscriber', methods=['POST'])
def register_subscriber():
    try:
        data = request.get_json()
        email = data.get('email')
        if email:
            register_new_subscriber(email)
            return jsonify({"message": "New Subscriber registered successfully"}), 200
        else:
            return jsonify({"error": "No email provided"}), 400
    except Exception as e:
        print(f"Registration failed: {str(e)}")
        return jsonify({"error": "Internal server error occurred"}), 500


def register_new_subscriber(email):
    print("register_new_subscriber")
    subscriber_exists = False
    try:
        existing_subscriber = mailerlite.subscribers.get(email)
        if existing_subscriber.get('data') or ('message' not in existing_subscriber):
            subscriber_exists = True
    except Exception as e:
        print(f"Error checking for existing subscriber: {str(e)}")

    if not subscriber_exists:
        mailerlite.subscribers.create(email=email)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"login_required: Checking login for access to {f.__name__}")
        if 'uid' not in session:
            print("login_required: No user ID in session, redirecting to login")
            session['nextUrl'] = request.url
            return redirect(url_for('login'))
        
        print(f"login_required: User ID found in session")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        @login_required
        def inner(*args, **kwargs):
            print(f"admin_required: Checking admin privileges")
            if not session.get('is_admin', False):
                return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
                # For web pages maybe use a redirect:
                # return redirect(url_for('some_route_name'))
            return f(*args, **kwargs)
        return inner(*args, **kwargs)
    return decorated_function


def check_admin_privileges(uid):
    user = auth.get_user(uid)
    if user.custom_claims:
        return user.custom_claims.get('admin', False)
    else:
        return False
    
@app.route('/reset-next-url')
def reset_next_url():
    session.pop('nextUrl', None)
    return ('', 204)


@app.route('/check-profile-completion', methods=['POST'])
@login_required
def check_profile_completion():
    try:
        user_uid = session.get('uid')
        user_record = auth.get_user(user_uid)

        try:
            existing_subscriber = mailerlite.subscribers.get(user_record.email)
            is_in_database = bool(existing_subscriber and existing_subscriber.get('data'))
        except Exception as e:
            print(f"Error fetching subscriber information: {str(e)}")
            is_in_database = False

        user_details_ref = db.reference(f'users/{user_uid}')
        user_details = user_details_ref.get()

        required_fields = ['contributor_status'] 
        is_complete = user_details and all(field in user_details for field in required_fields) and is_in_database
        return jsonify({'isComplete': is_complete}), 200
    except Exception as e:
        print(f"Error checking profile completion: {str(e)}")
        return jsonify({'error': 'Could not check profile completion'}), 500


@app.route('/complete-profile', methods=['GET'])
@login_required
def complete_profile():
    return render_template('complete-profile.html')


@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    user_uid = session.get('uid')
    user_data = getUserData(user_uid)

    return render_template('settings/settings-profile.html', user_data=user_data)


def getUserData(user_uid):
    user_data = {}
    if user_uid:
        user_record = auth.get_user(user_uid)
        user_data['uid'] = user_uid
        user_data['displayName'] = user_record.display_name
        user_data['email'] = user_record.email
        
        user_details_ref = db.reference(f'users/{user_uid}')
        user_details = user_details_ref.get()
        if(user_details):
            user_data.update(user_details)

    return user_data


@app.route('/settings/account', methods=['GET', 'POST'])
@login_required
def settings_account():
    user_uid = session.get('uid')
    user_data = {}

    if user_uid:
        user_record = auth.get_user(user_uid)
        user_data['uid'] = user_uid
        user_data['email'] = user_record.email
        user_data['displayName'] = user_record.display_name

    return render_template('settings/settings-account.html', user_data=user_data)


@app.route('/settings/my-videos', methods=['GET'])
@login_required
def settings_my_videos():
    user_uid = session.get('uid')
    user_data = {}

    if user_uid:
        user_record = auth.get_user(user_uid)
        user_data['uid'] = user_uid
        user_data['email'] = user_record.email
        user_data['displayName'] = user_record.display_name
        
        user_details_ref = db.reference(f'users/{user_uid}')
        user_details = user_details_ref.get()
        user_data.update(user_details)

    climber_id = user_data.get('climber_id')
    if(climber_id):
        url = "/contributors/" + slugify(climber_id)
        return redirect(url)
    else:
        print("Error loading my videos: No climber_id found")
        return redirect("/settings/profile")
    
    
@app.route('/settings/stats', methods=['GET'])
@login_required
def settings_stats():
    user_uid = session.get('uid')
    user_data = {}

    if user_uid:
        user_record = auth.get_user(user_uid)
        user_data['uid'] = user_uid
        user_data['email'] = user_record.email
        user_data['displayName'] = user_record.display_name

        account_creation_timestamp = user_record.user_metadata.creation_timestamp / 1000 # Convert from milliseconds to seconds
        account_creation_date = datetime.fromtimestamp(account_creation_timestamp)
        user_data['dateCreated'] = account_creation_date.strftime('%Y-%m-%d')

        time_since_creation = datetime.now() - account_creation_date
        user_data['timeSinceCreation'] = str(time_since_creation.days) + " days"
        
        user_details_ref = db.reference(f'users/{user_uid}')
        user_details = user_details_ref.get()
        user_data.update(user_details)

        contributor_stats = utils.zone_helpers.calculate_contributor_stats(user_data['climber_id'])
        user_data['contributor_stats'] = contributor_stats
        user_data['total_contributors'] = utils.MadBoulderDatabase.getContributorsCount()

    return render_template("/settings/settings-stats.html", user_data=user_data)


@app.route('/settings/projects', methods=['GET'])
@login_required
def settings_projects():
    user_uid = session.get('uid')
    projectIds = utils.MadBoulderDatabase.getProjects(user_uid)
    projectsList = []
    print(projectIds)

    if projectIds:
        for problemId in projectIds:
            videoData = utils.MadBoulderDatabase.getVideoDataWithSlug(problemId)
            if videoData:
                projectsList.append(videoData)
            else:
                print(f"Data for problem ID {problemId} not found.")
    print(projectsList)

    return render_template("/settings/settings-projects.html", projects=projectsList)


@app.route('/settings/admin/users', methods=['GET'])
@admin_required
def settings_admin_users():
    users_list, admins_list = get_all_users()
    contributors = utils.MadBoulderDatabase.getContributorNames()
    return render_template('settings/settings-admin-users.html', users_list=users_list, contributors=contributors)


@app.route('/settings/admin/admins', methods=['GET'])
@admin_required
def settings_admin_admins():
    users_list, admins_list = get_all_users()
    return render_template('settings/settings-admin-admins.html', users_list=users_list, admins_list=admins_list)


def get_all_users():
    users_list = []
    admins_list = []

    page = auth.list_users()
    while page:
        for user_record in page.users:
            uid = user_record.uid

            user_info = {
                'uid': uid,
                'email': user_record.email,
                'displayName': user_record.display_name,
                'contributor_status': 'N/A',  # Default value
                'climber_id': 'N/A',  # Default value
                'profile_completed': False
            }

            user_details_ref = db.reference(f'users/{uid}')
            user_details = user_details_ref.get()
            if user_details:
                user_info['contributor_status'] = user_details.get('contributor_status', 'N/A')
                user_info['climber_id'] = user_details.get('climber_id', 'N/A')
                user_info['profile_completed'] = True

            users_list.append(user_info)

            if check_admin_privileges(uid):
                admins_list.append(user_info)

        page = page.get_next_page()
    return users_list, admins_list


@app.route('/settings/admin/urls', methods=['GET'])
@admin_required
def settings_admin_urls():
    print("settings_admin_urls")
    urlMappings = utils.MadBoulderDatabase.getUrlMappings()
    return render_template('settings/settings-admin-urls.html', urlMappings=urlMappings)


@app.route('/settings/admin/missing-areas', methods=['GET'])
@admin_required
def settings_admin_missing_areas():
    print("settings_admin_missing_areas")
    sortedMissingAreasCount = utils.helpers.getMissingAreasCount()
    return render_template('settings/settings-admin-missing-areas.html', sortedMissingAreasCount=sortedMissingAreasCount)


@app.route('/update-slug', methods=['POST'])
@admin_required
def update_slug():
    print(request)
    data = request.get_json()
    print(data)
    oldSlug = data.get('oldSlug')
    newSlug = data.get('newSlug')
    
    try:
        utils.MadBoulderDatabase.addSlug(oldSlug, newSlug)
        return jsonify({'status': 'success', 'message': 'Slug updated successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/delete-slug', methods=['POST'])
@admin_required
def delete_slug():
    data = request.get_json()
    oldSlug = data.get('oldSlug')
    
    utils.MadBoulderDatabase.deleteSlug(oldSlug)
    return jsonify({'status': 'success', 'message': 'Slug deleted successfully'})


def get_user_uid(id_token):
    decoded_token = auth.verify_id_token(id_token)
    uid = decoded_token['uid']
    return uid


@app.route('/set-admin-claim/<userid>', methods=['POST'])
@admin_required
def add_admin_privileges(userid):
    try:
        auth.set_custom_user_claims(userid, {'admin': True})
        return jsonify({'status': 'success', 'message': 'Admin privileges added successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/revoke-admin-claim/<userid>', methods=['POST'])
@admin_required
def revoke_admin_privileges(userid):
    try:
        auth.set_custom_user_claims(userid, None)
        return jsonify({'status': 'success', 'message': 'Admin privileges revoked successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/update_user', methods=['POST'])
@login_required
def update_user():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    user_uid = session.get('uid')
    try:
        if 'displayName' in data:
            auth.update_user(user_uid, display_name=data['displayName'])

    except FirebaseError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    if request.is_json:
        return jsonify({'status': 'success', 'message': 'User updated successfully'})


@app.route('/update_user_details', methods=['POST'])
@login_required
def update_user_details():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
        
    user_uid = session.get('uid')

    updates = {}
    if 'contributor_status' in data and data['contributor_status'] != 'approved':
        updates['contributor_status'] = data['contributor_status']
        if data['contributor_status'] == 'pending':
            user_record = auth.get_user(user_uid)
            mail.sendPendingContributor(user_record.email)

    if updates:
        user_details_ref = db.reference(f'users/{user_uid}')
        user_details_ref.update(updates)

    if request.is_json:
        return jsonify({'status': 'success', 'message': 'User updated successfully'})


@app.route('/update_user_details_protected', methods=['POST'])
@admin_required
def update_user_details_protected():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    uid = data.get('uid')

    updates = {}
    if 'contributor_status' in data:
        updates['contributor_status'] = data['contributor_status']

    if 'climber_id' in data:
        updates['climber_id'] = data['climber_id']

    if updates:
        user_details_ref = db.reference(f'users/{uid}')
        user_details_ref.update(updates)

    if data['contributor_status'] == 'approved':
        if 'climber_id' in data:
            climber_id = data['climber_id']
            user_record = auth.get_user(uid)
            mail.sendContributorApproved(user_record.email, climber_id)

    if request.is_json:
        return jsonify({'status': 'success', 'message': 'User updated successfully'})
    

@app.route('/complete-profile-info', methods=['POST'])
@login_required
def complete_profile_info():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
        
    user_uid = session.get('uid')
    data = request.get_json()
    name = data.get('name', '')
    isContributor = data.get('isContributor', False)
    wantsNewsletter = data.get('wantsNewsletter', False)

    try:
        auth.update_user(user_uid, display_name=name)

        updates = {}
        if isContributor:
            updates['contributor_status'] = "pending"

            user_record = auth.get_user(user_uid)
            mail.sendPendingContributor(user_record.email)
        else:
            updates['contributor_status'] = "non contributor"

        if updates:
            user_details_ref = db.reference(f'users/{user_uid}')
            user_details_ref.update(updates)

        if wantsNewsletter:
            user_record = auth.get_user(user_uid)
            register_new_subscriber(user_record.email)

        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        print(e)
        return jsonify({'error': 'Failed to update profile'}), 500
    
    
@app.route('/submit-rating', methods=['POST'])
@login_required
def submit_rating():
    print("submit_rating")
    try:
        user_uid = session.get('uid')  # Get user ID from session

        data = request.get_json()
        problem_id = data.get('problem_id')
        rating = data.get('rating')

        if not problem_id or rating is None:
            return jsonify({'status': 'error', 'message': 'Missing problem ID or rating'}), 400
        
        if not (0 <= rating <= 5):
            return jsonify({'status': 'error', 'message': 'Rating must be a number between 0 and 5'}), 400

        utils.MadBoulderDatabase.submitRating(problem_id, user_uid, rating)

        return jsonify({"status": "success", "message": "Rating submitted"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/delete-rating', methods=['POST'])
@login_required
def delete_rating():
    user_uid = session.get('uid')
    data = request.get_json()
    problem_id = data.get('problem_id')

    if not problem_id or not user_uid:
        return jsonify({'status': 'error', 'message': 'Missing problem ID or user ID'}), 400

    utils.MadBoulderDatabase.deleteRating(problem_id, user_uid)
    return jsonify({'status': 'success', 'message': 'Rating deleted successfully'}), 200
    
    
@app.route('/submit-comment', methods=['POST'])
@login_required
def submit_comment():
    try:
        user_uid = session.get('uid')  # Get user ID from session

        data = request.get_json()
        problem_id = data.get('problem_id')
        comment = data.get('comment')

        if not problem_id or not comment:
            return jsonify({'status': 'error', 'message': 'Missing problem ID or comment text'}), 400
        
        new_comment_id = utils.MadBoulderDatabase.submitComment(problem_id, user_uid, comment)
        return jsonify({"status": "success", 'comment_id': new_comment_id, "message": "Comment submitted"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/delete-comment', methods=['POST'])
@login_required
def delete_comment():
    data = request.get_json()
    user_uid = session.get('uid')
    problem_id = data.get('problem_id')
    comment_id = data.get('comment_id')

    if not user_uid or not problem_id or not comment_id:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    utils.MadBoulderDatabase.deleteComment(problem_id, user_uid, comment_id)
    return jsonify({'status': 'success', 'message': 'Comment deleted successfully'}), 200
    
    
@app.route('/check-subscription-status', methods=['POST'])
@login_required
def check_subscription_status():
    user_uid = session.get('uid')

    try:
        user_record = auth.get_user(user_uid)
        print(user_record)
        subscriber = mailerlite.subscribers.get(user_record.email)
        subscriber_data = subscriber.get('data', {})
        if subscriber_data.get('status') == 'active':
            return jsonify({"subscribed": True}), 200
        else:
            return jsonify({"subscribed": False}), 200
    except Exception as e:
        print(f"Error checking subscription status: {str(e)}")
        return jsonify({"error": "Internal server error occurred"}), 500


@app.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    print("unsubscribe")
    data = request.get_json()
    user_email = data.get('email')
    try:
        unsubscribed = unsubscribe(user_email)
        if unsubscribed:
            return jsonify({"message": "Successfully unsubscribed from newsletter"}), 200
        else:
            return jsonify({"message": "Email not found in subscription list"}), 200
    except Exception as e:
        print(f"Unsubscribe failed: {str(e)}")
        return jsonify({"error": "Internal server error occurred"}), 500


def unsubscribe(email):
    subscriber = mailerlite.subscribers.get(email)
    if subscriber:
        subscriber_data = subscriber.get('data', {})
        if subscriber_data:
            mailerlite.subscribers.delete(int(subscriber_data.get('id')))
        return True
    return False


@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user_uid = session.get('uid')
    try:
        data = request.get_json()
        unsubscribe_newsletter = data.get('unsubscribeNewsletter', True)
        if unsubscribe_newsletter:
            user_record = auth.get_user(user_uid)
            unsubscribe(user_record.email)

        user_details_ref = db.reference(f'users/{user_uid}')
        user_details_ref.delete()
        auth.delete_user(user_uid)

        session.clear()

        return jsonify({'status': 'success', 'message': 'Your account has been successfully deleted.'})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'message': 'Failed to delete account.'}), 500


@app.route('/remove_user/<userId>', methods=['POST'])
@admin_required
def remove_user(userId):
    try:
        user_record = auth.get_user(userId)
        unsubscribe(user_record.email)
        user_ref = db.reference(f'users/{userId}')
        user_ref.delete()
        firebase_admin.auth.delete_user(userId)

        return jsonify({"success": True}), 200
    except firebase_admin.exceptions.FirebaseError as e:
        print(f"Error removing user: {e}")
        return jsonify({"error": "Failed to remove user"}), 500
    

@app.route('/add-problem-to-projects', methods=['POST'])
@login_required
def add_problem_to_projects():
    user_uid = session.get('uid')
    data = request.get_json()
    try:
        problem_id = request.json.get('problem_id')
        if not problem_id:
            raise ValueError('No problem ID provided')
        
        utils.MadBoulderDatabase.addProject(user_uid, problem_id)
        return jsonify({'status': 'success', 'message': 'Problem added to Projects'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/remove-problem-from-projects', methods=['POST'])
@login_required
def remove_problem_from_projects():
    user_uid = session.get('uid')
    data = request.get_json()
    problem_id = data.get('problem_id')

    try:
        if not problem_id:
            raise ValueError('No problem ID provided')
        
        utils.MadBoulderDatabase.deleteProject(user_uid, problem_id)
        return jsonify({'status': 'success', 'message': 'Problem removed from Projects'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/add-area')
@app.route('/edit-area/<string:areaCode>')
@app.route('/area-editor', methods=['GET'])
@admin_required
def area_editor(areaCode=None):
    rockTypeMapping = utils.zone_helpers.getRockTypeList()
    countries = utils.MadBoulderDatabase.getCountriesData()
    if areaCode:
        area = utils.MadBoulderDatabase.getAreaData(areaCode)
        print(area)
        action = "Edit"
    else:
        area = {}
        action = "Create"
    return render_template('area-editor.html', rockTypes=rockTypeMapping, countries=countries, area=area, action=action)


@app.route('/submit-area', methods=['POST'])
@admin_required
def submit_area():
    print("submit_area")
    try:
        data = request.get_json()
        print(data)
        areaName = data['name']
        areaCode = slugify(areaName)
        areaData = {
            "name": areaName,
            "zone_code": areaCode,
            "country": data['countryCode'],
            "state": data.get('stateCode', ''),
            "latitude": data['latitude'],
            "longitude": data['longitude'],
            "altitude": data['altitude'],
            "zoom": data['zoom'],
            "rock_type": data['rock_type'],
            "overview": [
                data['overview_en'],
                data['overview_es']
            ],
            "parkings": json.loads(data['parkings']),
            "links": json.loads(data['links']),
            "guides": json.loads(data['guides'])
        }
        print(areaData)
        utils.MadBoulderDatabase.addArea(areaCode, areaData)
        return jsonify({"status": "success", "message": "Area added successfully!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/fetch-altitude')
def fetch_altitude():
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    url = f"https://api.opentopodata.org/v1/aster30m?locations={latitude},{longitude}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch data'}), response.status_code
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500
    
    
@app.route('/get-countries')
def get_countries():
    countries = utils.MadBoulderDatabase.getCountriesData()
    return jsonify(countries=countries)


@app.route('/add-country', methods=['POST'])
def add_country():
    try:
        data = request.get_json()
        countryReducedCode = data['reduced_code'].lower()
        countryCode = slugify(data['name'][0])

        countryData = {
            'name': data['name'],
            'overview': data['overview'],
            'reduced_code': countryReducedCode
        }

        utils.MadBoulderDatabase.updateCountry(countryCode, countryData)
        return jsonify({'status': 'success', 'message': 'Country added successfully'}), 200
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to add country'}), 500
    


@app.route('/add-state', methods=['POST'])
def add_state():
    try:
        data = request.get_json()
        countryCode = data['country']
        stateCode = slugify(data['name'][0])

        stateData = {
            'name': data['name']
        }

        utils.MadBoulderDatabase.updateState(countryCode, stateCode, stateData)
        return jsonify({'status': 'success', 'message': 'Country added successfully'}), 200
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to add country'}), 500


@app.route('/<string:sitemap_name>.xml')
def sitemap_file(sitemap_name):
    if re.match(r'sitemap(-\w+)?', sitemap_name):
        print(sitemap_name)
        sitemap_filename = f'{sitemap_name}.xml'   
        return send_file(sitemap_filename, mimetype='application/xml')
    else:
        return "Invalid sitemap name"
    

@app.route('/countries.json')
def countries_json():
    file_path = os.path.join(app.root_path, 'data') + '/' + 'countries.json'
    return send_file(file_path)
    

@app.route('/random', methods=['GET', 'POST'])
def random_zone():
    if request.method == 'GET':
        zones = next(os.walk('data/zones/'))[1]
        all_zones = ['zones/' + area for area in zones]
        return render_template(random.choice(all_zones) + EXTENSION)


@app.route('/latest-news-and-videos')
def render_latest():
    return render_template('latest-news-and-videos.html', video_urls=utils.helpers.getLastVideosFromChannel())


@app.route('/weather-forecast-comparator')
@app.route('/bouldercast')#deprecated
@app.route('/weather-comparator')
@app.route('/weather-forecast-comparison-tool')
def show_weather_forecast_comparator():
    zones=get_zone_data()
    default_zones_param = request.args.get('defaultZones', '')
    if default_zones_param == '':
        default_zones_param = request.args.get('default', '')

    default_zones = default_zones_param.split(',') if default_zones_param else []
    
    if get_locale() == 'es':
       url = 'es/comparador-pronostico-tiempo.html'
    else:
        url = 'weather-forecast-comparator.html'


    return render_template(url, zones=zones, default_zones=default_zones)


@app.route('/es/comparador-pronostico-tiempo')
@app.route('/comparador-pronostico-tiempo')
def comparador_pronostico_tiempo():
    zones=get_zone_data()
    default_zones_param = request.args.get('default', '')

    default_zones = default_zones_param.split(',') if default_zones_param else []
    return render_template('/es/comparador-pronostico-tiempo.html', zones=zones, default_zones=default_zones)


@app.route('/element/weather-widget')
def weather_widget():
    file_path = os.path.join(app.root_path, 'templates/elements/weather-widget.html')
    return send_file(file_path)


@app.route('/bouldering-areas-map')
@app.route('/map')
def render_map():
    return render_template('bouldering-areas-map.html')


@app.route('/submit-support-form', methods=['POST'])
def submit_form():
    print("submit_form")
    recaptcha_token = request.form['g-recaptcha-response']
    project_id = 'madboulder'
    recaptcha_site_key = '6LcVBLIpAAAAAJZUryjl1eqk9x_QhBmOGoIpVSGa'
    recaptcha_action = 'submit_support_form'
    
    assessment = create_assessment(project_id, recaptcha_site_key, recaptcha_token, recaptcha_action)
    if assessment:
        try:
            mail.sendFeedback(request.form['name'], request.form['email'], request.form['feedback'])
            return render_template('thanks-for-joining.html')
        except Exception as e:
            print(str(e)) 
            abort(500, 'Internal Server Error') 

     
def create_assessment(
    project_id: str, recaptcha_key: str, token: str, recaptcha_action: str
) -> Assessment:
    """Create an assessment to analyze the risk of a UI action.
    Args:
        project_id: Your Google Cloud Project ID.
        recaptcha_key: The reCAPTCHA key associated with the site/app
        token: The generated token obtained from the client.
        recaptcha_action: Action name corresponding to the token.
    """

    # Set the properties of the event to be tracked.
    event = recaptchaenterprise_v1.Event()
    event.site_key = recaptcha_key
    event.token = token

    assessment = recaptchaenterprise_v1.Assessment()
    assessment.event = event

    project_name = f"projects/{project_id}"

    # Build the assessment request.
    request = recaptchaenterprise_v1.CreateAssessmentRequest()
    request.assessment = assessment
    request.parent = project_name

    response = recaptcha_client.create_assessment(request)

    if not response.token_properties.valid:
        print(
            "The CreateAssessment call failed because the token was "
            + "invalid for the following reasons: "
            + str(response.token_properties.invalid_reason)
        )
        abort(400, 'The reCAPTCHA token was invalid.')

    if recaptcha_action and response.token_properties.action != recaptcha_action:
        print("The action attribute did not match the expected action.")
        abort(400, 'The reCAPTCHA action did not match the expected action.')

    score = response.risk_analysis.score
    print(f"The reCAPTCHA score for this token is: {score}")

    threshold_score = 0.5
    if score < threshold_score:
        print("The reCAPTCHA score was below the threshold for trustworthiness.")
        abort(400, 'The reCAPTCHA score indicated the submission was not trustworthy.')

    return response


@app.route('/about-us', methods=['GET'])
def render_about_us():
    stats_list = [
        {
            'text': _('Zones'),
            'data': utils.MadBoulderDatabase.getAreasCount()
        },
        {
            'text': _('Contributors'),
            'data': utils.MadBoulderDatabase.getContributorsCount()
        },
        {
            'text': _('Videos'),
            'data': utils.MadBoulderDatabase.getVideoCount()
        }
    ]
    return render_template('about-us.html', stats_list=stats_list)
    
    
@app.route('/join-us', methods=['GET', 'POST'])
@app.route('/join_us', methods=['GET', 'POST'])
def join_us():
    if request.method == 'POST':
        try:
            mail.sendjoinUs(request.form['name'], 
                            request.form['message'], 
                            request.form['email'], 
                            request.files['resume'])
            return render_template('thanks-for-joining.html')
        except Exception as e:
            print("An error occurred:", e)
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


@app.route('/<string:page>')
@app.route('/templates/zones/<string:page>.html')
@app.route('/<string:page>.html')
def render_page(page):
    try:

        language_extension = ''
        if get_locale() == 'es':
            language_extension = 'es/'

        page_path = 'zones/' + language_extension + slugify(page) + EXTENSION
        print(page_path)

        return render_template(page_path)
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/es/<string:page>')
@app.route('/es/<string:page>.html')
@app.route('/templates/zones/es/<string:page>.html')
def render_page_es(page):
    try:
        page_path = 'zones/' + 'es/' + slugify(page) + EXTENSION
        return render_template(page_path)
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/problems/<string:area>/<string:problem_name>')
@app.route('/problems/<string:area>/<string:problem_name>.html')
def load_problem(area, problem_name):
    print("load problem", area, problem_name)
    try:
        problemSlug = utils.MadBoulderDatabase.getProblemSlug(area, problem_name)
        if problemSlug:
            user_uid = session.get('uid')
            if user_uid:
                problem_in_projects = is_problem_in_projects(user_uid, problemSlug)
            else:
                problem_in_projects = False
            
            comments = get_comments_for_problem(problemSlug)
            ratings = get_ratings_for_problem(problemSlug, user_uid)

            url = "problems/" + problemSlug + ".html"
            return render_template(url, problem_in_projects=problem_in_projects, ratings=ratings, comments=comments)
        else:
            print("Problem not found:", area + '/' + problem_name)
            abort(404)


    except Exception as e:
        print("An error occurred loading problem:", e)
        abort(404)


def is_problem_in_projects(user_id, problem_id):
    print("is_problem_in_projects")
    project = utils.MadBoulderDatabase.getProject(user_id, problem_id)
    print(project is not None)
    return project is not None


def get_ratings_for_problem(problem_id, user_uid=None):
    print("get_ratings_for_problem")
    ratings = utils.MadBoulderDatabase.getRatings(problem_id)
    print(ratings)

    if not ratings:
        return {'average_rating': 0, 'total_votes': 0, 'user_rating': None, 'has_rated': False}

    total_rating = sum(float(rating) for rating in ratings.values())
    total_votes = len(ratings)
    average_rating = total_rating / total_votes if total_votes else 0

    user_rating = ratings.get(user_uid) if user_uid in ratings else None
    has_rated = user_uid in ratings

    return {
        'average_rating': average_rating,
        'total_votes': total_votes,
        'user_rating': user_rating,
        'has_rated': has_rated
    }


def get_comments_for_problem(problem_id):
    print("get_comments_for_problem")
    comments = utils.MadBoulderDatabase.getComments(problem_id)

    if comments is None:
        return []
    else:
        for comment_id, comment in comments.items():
            comment['user_name'] = get_user_display_name(comment['user_uid'])
        return [{'id': key, **value} for key, value in comments.items()]
    

def get_user_display_name(user_uid):
    user_record = auth.get_user(user_uid)
    return user_record.display_name
    

@app.route('/sectors/<string:page>/<string:sector_name>')
@app.route('/templates/sectors/<string:page>/<string:sector_name>.html')
@app.route('/sectors/<string:page>/<string:sector_name>.html')
@app.route('/<string:page>/sector/<string:sector_name>') #deprecated
def load_sector(page, sector_name):
    try:
        return render_template(f'sectors/{slugify(page)}/{slugify(sector_name)}.html')
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/boulders/<string:page>/<string:boulder_code>')
@app.route('/templates/boulders/<string:page>/<string:boulder_code>.html')
@app.route('/boulders/<string:page>/<string:boulder_code>.html')
def load_boulder(page, boulder_code):
    try:
        return render_template(f'boulders/{slugify(page)}/{slugify(boulder_code)}.html')
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/countries/<string:country_name>')
@app.route('/templates/countries/<string:country_name>.html')
def load_country(country_name):
    try:

        language_extension = ''
        if get_locale() == 'es':
            language_extension = 'es/'

        page_path = 'countries/' + language_extension + slugify(country_name) + EXTENSION
        print(page_path)

        return render_template(page_path)
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/countries/es/<string:country_name>')
@app.route('/templates/countries/es/<string:country_name>.html')
def load_country_es(country_name):
    try:
        return render_template(f'countries/es/{slugify(country_name)}.html')
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/states/<string:state_name>')
@app.route('/templates/states/<string:state_name>.html')
def load_state(state_name):
    try:
        return render_template(f'states/{slugify(state_name)}.html')
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/contributors/<string:contributor_name>')
@app.route('/templates/contributors/<string:contributor_name>.html')
def load_contributor(contributor_name):
    try:
        return render_template(f'contributors/{slugify(contributor_name)}.html')
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


# this route is used for rendering maps inside an iframe
@app.route('/maps/<string:area>')
@app.route('/maps/<string:area>.html')
@app.route('/templates/maps/<string:area>.html')
@app.route('/es/maps/<string:area>')
@app.route('/es/maps/<string:area>.html')
@app.route('/es/templates/maps/<string:area>.html')
def render_area(area):
    try:
        return render_template('maps/' + area + EXTENSION)
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/download/<string:path>/<string:filename>')
def download_file(path=None, filename=None):
    try:
        download_path = os.path.join(app.root_path, 'data/zones/' + path) + '/' + filename
        return send_file(download_path, as_attachment=False)
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.errorhandler(404)
def page_not_found(error):
    app.logger.error('Page not found: %s', (request.path))
    return render_template('errors/404-page-not-found.html'), 404


@app.route('/preview-video/<filename>')
def preview_video(filename):
    return send_from_directory(app.config['LOCAL_VIDEOS_FOLDER'], filename)


@app.route('/list-local-videos')
def list_local_videos():
    try:
        videos_dir = Path(app.config['LOCAL_VIDEOS_FOLDER'])
        
        # List all video files (add more extensions if needed)
        videos = []
        for ext in ['.mp4', '.mov']:
            videos.extend([f.name for f in videos_dir.glob(f'*[{ext.lower()}{ext.upper()}]')])
        # Remove any duplicates that might still occur
        videos = list(dict.fromkeys(videos))
        return jsonify(videos=videos)
    except Exception as e:
        print(f"Error listing videos: {str(e)}")
        traceback.print_exc()  # This will print the full error stack
        return jsonify({'error': str(e)}), 500


# start the server
if __name__ == '__main__':
    # Start the Flask application
    app.run(debug=False)
