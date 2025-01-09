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
            fields="name, properties, thumbnailLink"
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
    

def empty():
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


def bytes_to_mb(bytes_value):
    """Convert bytes to megabytes."""
    return bytes_value / (1024 * 1024)