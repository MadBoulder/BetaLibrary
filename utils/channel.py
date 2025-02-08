import os
from flask import url_for, redirect
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
import utils.helpers

from google_auth_oauthlib.flow import Flow


load_dotenv()

YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY_HANDLE_DATA']
MAX_ITEMS_API_QUERY = 50
CLIENT_SECRET_FILE = 'madboulder_channel.json'
API_NAME = 'youtube'
API_VERSION = 'v3'
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube'
]
TOKEN_FILE = 'token.json'

youtube = build(API_NAME, API_VERSION, developerKey=YOUTUBE_API_KEY)
channelId='UCX9ok0rHnvnENLSK7jdnXxA'


def fetchChannelTotalVideoCount():
    response = youtube.channels().list(
        part='statistics',
        id=channelId
    ).execute()
    return int(response['items'][0]['statistics']['videoCount'])

def getUploadPlaylistId():
    response = youtube.channels().list(
        part='contentDetails',
        id=channelId
    ).execute()
    return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']


def fetchVideoByDate(publishedAfter, pageToken=None):
    response = youtube.search().list(
        part='snippet',
        channelId=channelId,
        maxResults=MAX_ITEMS_API_QUERY,
        type='video',
        order='date',
        pageToken=pageToken,
        publishedAfter=publishedAfter,
        fields="nextPageToken,items(id/videoId)"
    ).execute()
    return response


def fetchLastPublishedVideos(numVideos=6):
    response = youtube.search().list(
        part='snippet,id',
        channelId=channelId,
        maxResults=numVideos,
        order='date',
        type='video'
    ).execute()
    return response


def fetchAllVideoIds(uploadPlaylistId, pageToken=None):
    response = youtube.playlistItems().list(
        part='contentDetails',
        playlistId=uploadPlaylistId,
        maxResults=MAX_ITEMS_API_QUERY,
        pageToken=pageToken
    ).execute()
    return response


def fetchPlaylists(pageToken=None):
    response = youtube.playlists().list(
            part="snippet, contentDetails",
            channelId=channelId,
            maxResults=MAX_ITEMS_API_QUERY,
            pageToken=pageToken
        ).execute()
    return response


def fetchVideoDetails(videoIds):
    if isinstance(videoIds, str):
        videoIds = [videoIds]

    response = youtube.videos().list(
        part='snippet,statistics,status',
        id=','.join(videoIds)
    ).execute()
    return response


def searchForVideosByName(videoName, results=5):
    response = youtube.search().list(
        q=videoName,
        part='snippet',
        channelId=channelId,
        maxResults=results,
        type='video'
    ).execute()
    return response


def addVideoToPlaylist(videoId, playlistId):
    try:
        credentials = getCredentials()
        youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)

        request = youtubeOauth.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlistId,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": videoId
                    }
                }
            }
        )
        return request.execute()
    except Exception as e:
        print(f"Error adding video to playlist {videoId}: {e}")
        return None



def enableMonetization(videoId):
    try:
        credentials = getCredentials()
        youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)
        request_body = {
            "id": videoId,
            "status": {
                "selfDeclaredMadeForKids": False,
                "monetizationDetails": {
                    "access": "allowed"
                }
            }
        }

        response = youtubeOauth.videos().update(
            part="status",
            body=request_body
        ).execute()

        print(f"Monetization enabled for video: {videoId}")
        return response
    except Exception as e:
        print(f"Error enabling monetization for video {videoId}: {e}")
        return None


def getEmbedUrl(id):
    return f"https://www.youtube.com/embed/{id}"


def getUrl(id):
    return f"https://www.youtube.com/watch?v={id}"


def uploadVideo(video_stream, title, description, tags, privacy_status, publish_time=None):
    """Upload a video to YouTube"""
    try:
        credentials = getCredentials()
        youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '17'  # Sports category
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Add publishAt if we have a publish_time
        if publish_time:
            print(publish_time)
            # YouTube API expects RFC 3339 format
            body['status']['publishAt'] = publish_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            print(body)

        # Call the API's videos.insert method
        insert_request = youtubeOauth.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaIoBaseUpload(video_stream, 'video/*', resumable=True)
        )
        
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")
        
        print(f"Upload Complete! Video ID: {response['id']}")
        return response
        
    except Exception as e:
        print(f"Error uploading video: {e}")
        raise e


def getCredentials():
    credentials = None
    
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request()) # type: ignore
        
    return credentials


def is_authenticated():
    credentials = getCredentials()
    if not credentials:
        return False
    return credentials.valid


def authenticate(local):
    if local:
        credentials = getCredentials()
        if not credentials or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(
                port=53011,
                access_type='offline',
                prompt='consent'
            )
            saveToken(credentials)

        return redirect(url_for('upload_hub'))
    else:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=url_for('oauth2callback', _external=True)
        )
        authorization_url, _ = flow.authorization_url(prompt='consent')
        return redirect(authorization_url)


def oauth2callback(authorization_response):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=authorization_response)
    saveToken(flow.credentials)


def saveToken(credentials):
    with open(TOKEN_FILE, 'w') as token_file:
            token_file.write(credentials.to_json())


def getUploadedVideosUntilDaysBack(days_back=7):
    """Get list of videos published until a specified number of days back"""
    try:
        # Get authenticated client
        credentials = getCredentials()
        youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)
        
        uploads_playlist_id = getUploadPlaylistId()
        
        # Cache for video IDs
        video_ids = []
        next_page_token = None
        request_next_page = True
        now = datetime.utcnow()
        cutoff_date = now - timedelta(days=days_back)

        while request_next_page:
            request = youtubeOauth.playlistItems().list(
                part="snippet",  # Only need snippet to get video IDs
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            playlist_response = request.execute()

            # Store video IDs in the cache
            video_ids.extend([item['snippet']['resourceId']['videoId'] for item in playlist_response.get('items', [])])

            for item in playlist_response.get('items', []):
                snippet = item['snippet']
                upload_date = datetime.strptime(snippet['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')

                # Stop if we encounter a video older than `days_back`
                if upload_date < cutoff_date:
                    request_next_page = False
                    break

            # Continue paginating only if we haven't found an older video
            if request_next_page and playlist_response.get('nextPageToken'):
                next_page_token = playlist_response.get('nextPageToken')
            else:
                break

        print("Video IDs retrieved: ", video_ids)  # Log the video IDs
        return video_ids

    except Exception as e:
        print(f"Error fetching videos until days back: {e}")
        return []

def getVideoDetails(video_ids):
    # Query video details for all video IDs
    detailed_videos = []
    
    credentials = getCredentials()
    youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)

    if video_ids:
        # Split video_ids into chunks of 50 if necessary
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            try:
                video_response = youtubeOauth.videos().list(
                    part="snippet,status",  # Include both snippet and status
                    id=','.join(chunk)  # Join the chunk into a single string
                ).execute()

                # Combine data into detailed_videos
                for video in video_response.get('items', []):
                    detailed_videos.append(video)

            except Exception as e:
                print(f"Error fetching video details for IDs {chunk}: {e}")
                # Continue processing with whatever data has been retrieved so far

    # Return the detailed video information
    return detailed_videos


def getScheduledVideos(days_back=7):
    try:
        uploadedVideosIds = getUploadedVideosUntilDaysBack(days_back)
        uploadedVideosWithDetails = getVideoDetails(uploadedVideosIds)
        scheduled_videos = []

        now = datetime.utcnow()

        for item in uploadedVideosWithDetails:
            status = item['status']
            privacy_status = status['privacyStatus']

            if privacy_status == 'private':
                publish_at = status.get('publishAt')

                if publish_at:
                    publish_time = datetime.strptime(publish_at, '%Y-%m-%dT%H:%M:%SZ')

                    if publish_time > now:
                        video_id = item['id']
                        title = item['snippet']['title']
                        description = item['snippet']['description']
                        videoInfo = utils.helpers.ExtractInfoFromDescription(title, description)
                        videoInfo['id'] = video_id
                        videoInfo['title'] = title
                        videoInfo['scheduledTime'] = publish_time
                        videoInfo['type'] = 'Short' if videoInfo['isShort'] else 'Regular'
                        scheduled_videos.append(videoInfo)
                else:
                    print(f"Error: Video ID {video_id} is private but has no publishAt date.")

        print(f"Private and scheduled videos found: {len(scheduled_videos)}")
        return scheduled_videos

    except Exception as e:
        print(f"Error fetching private and scheduled videos: {e}")
        return []


def createPlaylist(area_name, privacy_status='public'):
    """Create a new playlist for the given area."""
    credentials = getCredentials()
    youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)
    try:
        # Define the request body for the playlist
        request_body = {
            'snippet': {
                'title': area_name,
                'description': f'Playlist for the bouldering area: {area_name}',
                'tags': ['bouldering', 'climbing', area_name],
                'defaultLanguage': 'en'
            },
            'status': {
                'privacyStatus': privacy_status  # Configurable privacy status
            }
        }

        # Call the YouTube API to create the playlist
        response = youtubeOauth.playlists().insert(
            part='snippet,status',
            body=request_body
        ).execute()

        # Validate response and log
        if 'id' in response:
            print(f"Playlist created successfully: ID={response['id']}, Title={area_name}")
            return response['id']
        else:
            print(f"Unexpected response structure: {response}")
            return None

    except HttpError as e:
        error_content = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
        print(f"An error occurred while creating the playlist: {error_content}")
        return None