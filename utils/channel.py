import os
import google.auth
from flask import url_for, redirect
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import requests
from google.auth.transport.requests import Request
from datetime import datetime
import json

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
    request.execute()


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


def get_scheduled_videos():
    """Get list of scheduled videos from YouTube"""
    try:
        # Get authenticated client
        credentials = getCredentials()
        youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)
        
        # Get the channel's uploads playlist ID
        uploads_response = youtubeOauth.channels().list(
            part='contentDetails',
            mine=True
        ).execute()
        
        uploads_playlist_id = uploads_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get videos until we find a published one
        video_ids = []
        next_page_token = None
        request_next_page = True
        
        while request_next_page:
            request = youtubeOauth.playlistItems().list(
                part="snippet,status",  # Include status to check privacy
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            playlist_response = request.execute()
            
            # Check each video's status
            for item in playlist_response.get('items', []):
                if item['status'].get('privacyStatus') == 'private':
                    video_ids.append(item['snippet']['resourceId']['videoId'])
                else:
                    # Found a public video, don't request next page
                    request_next_page = False
            
            # Only get next page if we haven't found a public video and there are more pages
            if request_next_page and playlist_response.get('nextPageToken'):
                next_page_token = playlist_response.get('nextPageToken')
            else:
                break
        
        if not video_ids:
            print("No private videos found")
            return []
            
        # Get full video details in batches
        scheduled_videos = []
        now = datetime.utcnow()
        
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i + 50]
            
            videos_response = youtubeOauth.videos().list(
                part="snippet,status",
                id=','.join(batch_ids),
                fields="items(id,snippet(title,description),status(privacyStatus,publishAt))"
            ).execute()
            
            for item in videos_response.get('items', []):
                status = item.get('status', {})
                snippet = item.get('snippet', {})
                
                # Check if video has a future publish date
                publish_at = status.get('publishAt')
                if publish_at:
                    publish_time = datetime.strptime(publish_at, '%Y-%m-%dT%H:%M:%SZ')
                    
                    if publish_time > now:
                        description = snippet.get('description', '')
                        metadata = parse_video_description(description)
                        
                        scheduled_videos.append({
                            'id': item['id'],
                            'title': snippet['title'],
                            'description': description,
                            'climber': metadata.get('climber'),
                            'name': metadata.get('name'),
                            'grade': metadata.get('grade'),
                            'zone': metadata.get('zone'),
                            'sector': metadata.get('sector'),
                            'scheduledTime': publish_time
                        })
        
        print("Scheduled videos found:", len(scheduled_videos))
        return scheduled_videos
        
    except Exception as e:
        print(f"Error fetching scheduled videos: {e}")
        print(f"Error details: {str(e)}")
        return []

def parse_video_description(description):
    """Extract metadata from video description"""
    metadata = {}
    
    # Split description into lines and look for metadata
    for line in description.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == 'climber':
                metadata['climber'] = value
            elif key == 'name':
                metadata['name'] = value
            elif key == 'grade':
                metadata['grade'] = value
            elif key == 'zone':
                metadata['zone'] = value
            elif key == 'sector':
                metadata['sector'] = value
    
    return metadata
