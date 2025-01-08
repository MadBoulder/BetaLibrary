
import os
import google.auth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


from google.oauth2.credentials import Credentials
from google.oauth2 import service_account


load_dotenv()

YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY_HANDLE_DATA']
MAX_ITEMS_API_QUERY = 50
CLIENT_SECRET_FILE = 'madboulder_channel.json'
API_NAME = 'youtube'
API_VERSION = 'v3'

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


def getEmbedUrl(id):
    return f"https://www.youtube.com/embed/{id}"


def getUrl(id):
    return f"https://www.youtube.com/watch?v={id}"


def uploadVideo(videoStream, title, description, tags, privacyStatus='private'):
    print("uploadVideo youtube")
    try:
        credentials = authenticate_youtube()
        youtube = build(API_NAME, API_VERSION, credentials=credentials)
        
        media_body = MediaIoBaseUpload(videoStream, mimetype='video/mp4', resumable=True)


        request = youtube.videos().insert(
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
        return response

    except Exception as e:
        raise Exception(f"Error uploading video to YouTube: {str(e)}")
    




SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
def authenticate_youtube():
    credentials = None
    # Check if the credentials are already saved (e.g. after the user has authenticated)
    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials, start the OAuth flow
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request()) # type: ignore
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=53011)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())

    return credentials