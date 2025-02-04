import io
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from google.oauth2 import service_account

CUSTOM_FOLDER_ID = '1OSocLiJSYTjVJHH_kv0umNFgTZ_G5wBB'

SERVICE_ACCOUNT_FILE = 'madboulder-f1887f0310ec.env'
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)


def getFileLink(file_id):
    return f'https://drive.google.com/file/d/{file_id}/view'


def getFileMetadata(file_id):
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields="name, properties, thumbnailLink, mimeType, videoMediaMetadata(durationMillis, width, height)"
        ).execute()
        return file_metadata
    except Exception as e:
        print(f"Error fetching file metadata: {e}")
        return None


def upload(file, renamed_filename, properties):
    print("upload_to_google_drive")
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        if drive_service:
            file_metadata = {
                'name': renamed_filename,
                'parents': [CUSTOM_FOLDER_ID],
                'properties': properties
            }
                             
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

            print("Upload of {} is complete.".format(renamed_filename))
            return response.get('id')
        else:
            raise Exception("Upload failed: Couldn't create Drive service")
    except Exception as e:
        raise Exception(e)
    

def getVideoStream(file_id):
    drive_service = build('drive', 'v3', credentials=credentials)
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download progress: {int(status.progress() * 100)}%")
    fh.seek(0)
    return fh
    

def get_storage_info():
    """Get Google Drive storage information in MB."""
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        quota = drive_service.about().get(fields='storageQuota').execute()['storageQuota']
        
        used_mb = int(quota['usage']) / (1024 * 1024)
        total_mb = int(quota['limit']) / (1024 * 1024)
        
        print(f"Drive space: {used_mb:.0f}MB / {total_mb:.0f}MB")
        return total_mb - used_mb
    except Exception as e:
        print(f"Failed to get storage info: {e}")
        return None


def check_storage():
    """Check if Google Drive available storage is below 200MB."""
    available = get_storage_info()
    if available is None:
        return False
    return available >= 200


def empty_trash():
    """Empty Google Drive trash to free up space."""
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        get_storage_info()  # Show storage before emptying
        
        print("Emptying trash...")
        drive_service.files().emptyTrash().execute()
        
        get_storage_info()  # Show storage after emptying
            
    except Exception as e:
        print(f"Failed to empty trash: {e}")


def empty_custom_folder():
    """Empty the custom folder and report storage changes."""
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        get_storage_info()  # Show storage before emptying
        
        # Delete files from custom folder
        file_list = drive_service.files().list(
            q=f"'{CUSTOM_FOLDER_ID}' in parents and trashed=false"
        ).execute().get('files', [])
        
        for file in file_list:
            print(f"Deleting file: {file.get('name', 'unnamed')}")
            drive_service.files().delete(fileId=file['id']).execute()

        drive_service.files().emptyTrash().execute()
        get_storage_info()  # Show storage after emptying
            
    except Exception as e:
        print(f"Failed to empty custom folder: {e}")