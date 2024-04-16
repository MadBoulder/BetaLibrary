
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY_HANDLE_DATA']
MAX_ITEMS_API_QUERY = 50

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
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
    return f"//www.youtube.com/embed/{id}"


def getUrl(id):
    return f"https://www.youtube.com/watch?v={id}"