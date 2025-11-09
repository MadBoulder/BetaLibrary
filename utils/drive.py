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
    """Display detailed Google Drive storage usage information in MB."""
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        about = drive_service.about().get(fields='storageQuota').execute()
        quota = about['storageQuota']

        total_mb = int(quota.get('limit', 0)) / (1024 * 1024)
        used_mb = int(quota.get('usage', 0)) / (1024 * 1024)
        used_in_drive_mb = int(quota.get('usageInDrive', 0)) / (1024 * 1024)
        used_in_trash_mb = int(quota.get('usageInDriveTrash', 0)) / (1024 * 1024)
        used_in_photos_mb = int(quota.get('usageInPhotos', 0)) / (1024 * 1024)

        print("\n=== Google Drive Storage Info ===")
        print(f"Total space:       {total_mb:.0f} MB")
        print(f"Used total:        {used_mb:.0f} MB")
        print(f"  • In Drive:      {used_in_drive_mb:.0f} MB")
        print(f"  • In Trash:      {used_in_trash_mb:.0f} MB")
        print(f"  • In Photos:     {used_in_photos_mb:.0f} MB")
        print(f"Free space:        {total_mb - used_mb:.0f} MB")
        print("=================================\n")

        return {
            "total": total_mb,
            "used_total": used_mb,
            "used_drive": used_in_drive_mb,
            "used_trash": used_in_trash_mb,
            "used_photos": used_in_photos_mb,
            "free": total_mb - used_mb
        }

    except Exception as e:
        print(f"Failed to get storage info: {e}")
        return None


def check_storage(threshold_mb=200):
    """Check if Google Drive available storage is below the threshold."""
    info = get_storage_info()
    if not info:
        print("Failed to retrieve storage info.")
        return False

    free_mb = info.get("free", 0)
    if free_mb < threshold_mb:
        print(f"Warning: Google Drive storage is below {threshold_mb}MB! (Free: {free_mb:.0f} MB)")
        return False

    print(f"Drive has {free_mb:.0f} MB free — OK.")
    return True


def empty_trash(max_retries=3, delay=5):
    """Empty Google Drive trash to free up space, with retry logic."""
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        get_storage_info()  # Show storage before emptying
        
        print("Emptying trash...")
        for attempt in range(1, max_retries + 1):
            try:
                drive_service.files().emptyTrash().execute()
                print("Trash emptied successfully.")
                break
            except HttpError as e:
                if e.resp.status in [500, 503]:
                    print(f"Attempt {attempt} failed due to internal error, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise
        else:
            print("Failed to empty trash after multiple retries.")
        
        get_storage_info()  # Show storage after emptying

    except Exception as e:
        print(f"Failed to empty trash: {e}")


def empty_custom_folder():
    """Clean all files owned by the service account to free space."""
    try:
        drive_service = build('drive', 'v3', credentials=credentials)

        print("\n--- BEFORE CLEANUP ---")
        get_storage_info()

        # Delete all files owned by the service account (trashed or not)
        print("\nDeleting all files owned by the service account...")
        page_token = None
        while True:
            results = drive_service.files().list(
                q="trashed=false",
                fields="nextPageToken, files(id, name, owners)",
                pageToken=page_token
            ).execute()
            for f in results.get('files', []):
                try:
                    print(f"Deleting {f['name']}")
                    drive_service.files().delete(fileId=f['id']).execute()
                except Exception as e:
                    print(f"Could not delete {f['name']}: {e}")
            page_token = results.get('nextPageToken', None)
            if not page_token:
                break

        print("\nEmptying trash...")
        try:
            drive_service.files().emptyTrash().execute()
        except Exception as e:
            print(f"Failed to empty trash: {e}")

        print("\n--- AFTER CLEANUP ---")
        get_storage_info()

    except Exception as e:
        print(f"Failed to empty custom folder: {e}")



        # start the server
if __name__ == '__main__':
    empty_custom_folder()
