
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


def uploadVideo(videoStream, title, description, tags, privacyStatus='private'):
    print("uploadVideo youtube")
    try:
        credentials = getCredentials()
        youtubeOauth = build(API_NAME, API_VERSION, credentials=credentials)
        
        media_body = MediaIoBaseUpload(videoStream, mimetype='video/mp4', resumable=True)


        request = youtubeOauth.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "17"
                },
                "status": {
                    "privacyStatus": privacyStatus
                }
            },
            media_body=media_body
        )

        response = request.execute()
        print("Upload successful:", response)
        return response

    except Exception as e:
        raise Exception(f"Error uploading video to YouTube: {str(e)}")
    

def getCredentials():
    credentials = None
    
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request()) # type: ignore
        
    return credentials

        if credentials.valid:
            return True
        
    return False

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