import json
import os
import random
import io
import threading
from flask import Flask, render_template, send_from_directory, request, abort, session, redirect, url_for, send_file, jsonify
from flask_caching import Cache
from flask_babel import Babel, _
from flask_mail import Mail,  Message
import firebase_admin
from firebase_admin import credentials, auth, db, exceptions
from firebase_admin.exceptions import FirebaseError
from urllib.parse import urlparse
from jinja2 import Environment, FileSystemLoader
import datetime
import utils.helpers
import utils.js_helpers
import utils.zone_helpers
import utils.MadBoulderDatabase
import dashboard
import dashboard_videos
import re
import time
from slugify import slugify
from functools import wraps
from dotenv import load_dotenv
import traceback
import requests

from bokeh.embed import components
from bokeh.resources import INLINE
import mailerlite as MailerLite

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account

from google.cloud import recaptchaenterprise_v1
from google.cloud.recaptchaenterprise_v1 import Assessment



EXTENSION = '.html'
EMAIL_SUBJECT_FIELDS = ['name', 'zone', 'climber']
REMOVE_FIRST = slice(1, None, 1)

load_dotenv()  # Take environment variables from .env.  

# create and configure the application object
app = Flask(__name__, static_folder='static')
app.config.from_pyfile('config.py')
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


@cache.cached(
    timeout=_get_seconds_to_next_time(hour=11, minute=10, second=00),
    key_prefix='mad_zones'
)
def get_zone_data():
    return utils.MadBoulderDatabase.get_zone_data()
def get_playlist_data():
    return utils.MadBoulderDatabase.get_playlist_data()

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


@app.route('/bouldering-areas-list', methods=['GET', 'POST'])
def zones():
    # TODO: POST and GET methods are handled equally
    # if request.method == 'GET':
    # if request.method == 'POST':
    # each zone has: link, name, num.videos
    zones = get_zone_data()
    playlists = get_playlist_data()
    country_data = utils.MadBoulderDatabase.get_country_data()
    return render_template(
        'bouldering-areas-list.html',
        zones=zones,
        playlists=playlists,
        countries=app.config['COUNTRIES'],
        country_data=country_data)


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
        max_score = 0.01

        def search_zone():
            search_zone_start_time = time.time()
            search_results['zones'] = utils.helpers.search_zone( query, max_score=max_score)
            search_zone_elapsed_time = time.time() - search_zone_start_time
            print(f"Search Zone execution time: {search_zone_elapsed_time} seconds")

        def search_sector():
            search_sector_start_time = time.time()
            search_results['sectors'] = utils.helpers.search_sector( query, max_score=max_score)
            search_sector_elapsed_time = time.time() - search_sector_start_time
            print(f"Search Sector execution time: {search_sector_elapsed_time} seconds")

        def search_problem():
            search_problem_start_time = time.time()
            search_results['problems'] = utils.helpers.search_problem( query, max_score=max_score)
            search_problem_elapsed_time = time.time() - search_problem_start_time
            print(f"Search Problem execution time: {search_problem_elapsed_time} seconds")
            for p in search_results['problems']:
                p['secure_slug'] = p['zone_code'] + '/' + slugify(p['name'] + '-'+ p['grade_with_info'])

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

        playlists=get_playlist_data()

        return render_template(
            'area-problem-finder.html',
            zones=search_results.get('zones', []),
            sectors=search_results.get('sectors', []),
            problems=search_results.get('problems', []),
            videos=search_results.get('videos', []),
            search_term=query,
            playlists=playlists
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
    user_uid = session.get('uid')
    user_data = getUserData(user_uid)
    return render_template('video-uploader.html', user_data=user_data)


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
            
            print("send email")
            mail.send(msg)
            return jsonify({"message": "File uploaded and processed successfully"}), 200
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            return jsonify({"error": "Internal server error occurred"}), 500
    else:
        return jsonify({"error": "File upload failed. Please check your request."}), 400


def upload_to_google_drive(file):
    print("upload_to_google_drive")
    try:
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
        

def bytes_to_mb(bytes_value):
    """Convert bytes to megabytes."""
    return bytes_value / (1024 * 1024)
        

def empty_google_drive():
    try:
        drive_service = build('drive', 'v3', credentials=credentials)

        about_info_before = drive_service.about().get(fields='storageQuota').execute()
        used_before_mb = bytes_to_mb(int(about_info_before['storageQuota']['usage']))
        total_space_mb = bytes_to_mb(int(about_info_before['storageQuota']['limit']))
        available_space_mb = total_space_mb - used_before_mb
        print(f"Drive space used before emptying: {used_before_mb:.2f} MB")
        print(f"Total drive space: {total_space_mb:.2f} MB")
        print(f"Available drive space before emptying: {available_space_mb:.2f} MB")
        
        
        file_list = drive_service.files().list(q="'root' in parents and trashed=false").execute().get('files', [])

        for file in file_list:
            print(file)
            drive_service.files().delete(fileId=file['id']).execute()

        drive_service.files().emptyTrash().execute()

        about_info_after = drive_service.about().get(fields='storageQuota').execute()
        used_after_mb = bytes_to_mb(int(about_info_after['storageQuota']['usage']))
        print(f"Drive space used after emptying: {used_after_mb:.2f} MB")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify({'progress': current_progress})


@app.route('/upload-completed', methods=['GET'])
def upload_completed():
    return render_template('thanks-for-uploading.html')


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
        account_creation_date = datetime.datetime.fromtimestamp(account_creation_timestamp)
        user_data['dateCreated'] = account_creation_date.strftime('%Y-%m-%d')

        time_since_creation = datetime.datetime.now() - account_creation_date
        user_data['timeSinceCreation'] = str(time_since_creation.days) + " days"
        
        user_details_ref = db.reference(f'users/{user_uid}')
        user_details = user_details_ref.get()
        user_data.update(user_details)

        contributor_stats = utils.zone_helpers.calculate_contributor_stats(user_data['climber_id'])
        user_data['contributor_stats'] = contributor_stats
        user_data['total_contributors'] = utils.MadBoulderDatabase.get_contributors_count()

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
    contributors = utils.MadBoulderDatabase.get_contributors_list()
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
            new_pending_contributor_notification(user_record.email)

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
            contributor_approved_notification(user_record.email, climber_id)

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
            new_pending_contributor_notification(user_record.email)
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
    

def new_pending_contributor_notification(email):
    msg_body = 'New Contributor Submission pending to approve from user: {}\n\nApprove the request in https://www.madboulder.org/settings/admin/users'.format(email)
        
    msg = Message(
        subject='MadBoulder New Contributor Submission',
        sender=app.config.get('MAIL_USERNAME'),
        recipients=app.config.get('FEEDBACK_MAIL_RECIPIENTS'),
        body=msg_body)
    mail.send(msg)
    

def contributor_approved_notification(email, climber_id):
    msg_body = 'Your Contributor Submission has been accepted and associated with the following climber id: {}\n\nYou can review it in https://www.madboulder.org/settings/profile'.format(climber_id)       
    msg = Message(
        subject='Contributor Submission Accepted!',
        sender=app.config.get('MAIL_USERNAME'),
        recipients=[email],
        body=msg_body)
    mail.send(msg)


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
    return render_template('latest-news-and-videos.html', video_urls=get_videos_from_channel())


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


@app.route('/element/weather-widget.html')
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
            feedback_data = request.form['feedback']
            sender_email = request.form['email']
            msg_body = 'Sender: {}\nMessage: {}'.format(
                sender_email, feedback_data)
            
            msg = Message(
                subject='madboulder.org feedback',
                sender=app.config.get('MAIL_USERNAME'),
                recipients=app.config.get('FEEDBACK_MAIL_RECIPIENTS'),
                body=msg_body)
            mail.send(msg)
            return render_template('thanks-for-joining.html')
        except Exception as e:
            print(str(e))  # Log the error for debugging
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
    zone_data = utils.MadBoulderDatabase.get_zone_data()
    stats_list = [
        {
            'text': _('Zones'),
            'data': len(zone_data)
        },
        {
            'text': _('Contributors'),
            'data': utils.MadBoulderDatabase.get_contributors_count()
        },
        {
            'text': _('Videos'),
            'data': utils.MadBoulderDatabase.get_video_count()
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

# video count is cached for one hour
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

        return render_template(page_path, current_url=page, stats_list=get_area_page_stats(page))
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


@app.route('/es/<string:page>')
@app.route('/es/<string:page>.html')
@app.route('/templates/zones/es/<string:page>.html')
def render_page_es(page):
    try:
        page_path = 'zones/' + 'es/' + slugify(page) + EXTENSION
        return render_template(page_path, current_url=page, stats_list=get_area_page_stats(page))
    except Exception as e:
        print("An error occurred:", e)
        abort(404)


def get_area_page_stats(page):
    try:
        zone_problems = utils.MadBoulderDatabase.getVideoDataFromZone(slugify(page))

        views_count = utils.zone_helpers.get_view_count_from_problems(zone_problems)
        contributor_count = utils.zone_helpers.get_contributor_count_from_problems(zone_problems)
        video_count = len(zone_problems)
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
                'logo': 'fas fa-user',
                'text': _('Contributors'),
                'data': contributor_count
            },
            {
                'logo': 'fa fa-map-marked',
                'text': _('Sectors'),
                'data': sector_count
            }]
    except Exception as e:
        print("An error occurred:", str(e))
        traceback.print_exc()

    return data


@app.route('/problems/<string:area>/<string:problem_name>')
@app.route('/problems/<string:area>/<string:problem_name>.html')
def load_problem(area, problem_name):
    print("load problem", area, problem_name)
    try:
        videoData = utils.MadBoulderDatabase.getVideoData(area, problem_name)
        if videoData:
            print(videoData)
            problem_id = videoData['secure_slug']

            user_uid = session.get('uid')
            if user_uid:
                problem_in_projects = is_problem_in_projects(user_uid, problem_id)
                comments = get_comments_for_problem(problem_id)
            else:
                comments = []
                problem_in_projects = False
            
            ratings = get_ratings_for_problem(problem_id, user_uid)

            url = "problems/" + videoData['secure_slug'] + ".html"
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


# start the server
if __name__ == '__main__':
    app.run(debug=False)
