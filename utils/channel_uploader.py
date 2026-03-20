from datetime import datetime
from flask import render_template
import utils.channel
import utils.MadBoulderDatabase
import re  # Add this import at the top of the file

def process_channel_upload(title, description, tags, scheduled_time, zone_code, sector_code, video_stream, progress_callback=None):
    """
    Common helper function to handle channel video uploads and playlist management.

    Args:
        title: Video title
        description: Video description
        tags: Video tags (as list)
        scheduled_time: Optional scheduled publish time
        zone_code: Zone code for playlist
        sector_code: Sector code for playlist
        video_stream: File-like object containing video data
        progress_callback: Optional callback(percent) for upload progress

    Returns:
        Tuple of (upload_response, publish_time, error_response)
    """
    try:
        # Convert scheduled_time string to datetime if it exists
        publish_time = None
        if scheduled_time:
            publish_time = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")

        # Upload to channel
        response = utils.channel.uploadVideo(
            video_stream=video_stream,
            title=title,
            description=description,
            tags=tags if isinstance(tags, list) else [t.strip() for t in tags.split(',')],
            privacy_status='private',
            publish_time=publish_time,
            progress_callback=progress_callback
        )

        if response is None:
            raise Exception("Video upload failed, no response received.")

        uploaded_video_id = response.get('id')
        if not uploaded_video_id:
            raise Exception("Upload response does not contain video ID.")

        print("video uploaded to channel")
        
        # Add to playlists
        print(f"adding video to playlist {zone_code}")
        playlists = utils.MadBoulderDatabase.getPlaylistData(zone_code)

        zone_playlist_id = playlists.get("id") if playlists else None
        sector_playlists = playlists.get("sectors", {}) if playlists else {}

        # Check if the zone playlist exists, if not create it
        if not zone_playlist_id:
            # Extract zone name from title using regex
            match = re.search(r',\s*[^.]+\. (.+)', title)  # Adjusted regex to capture the entire AreaName
            zone_name = match.group(1).strip() if match else None  # Extract AreaName or set to None if not found

            if not zone_name:
                print("Zone name could not be extracted from the title, falling back to zone_code.")
                zone_name = zone_code  # Fallback to zone_code if zone_name is not found

            zone_playlist_id = utils.channel.createPlaylist(zone_name)  # Use zone_name instead of zone_code
            if not zone_playlist_id:
                raise Exception(f"Failed to create playlist for zone: {zone_name}")
            else:
                print(f"Created new playlist for zone: {zone_name} with ID: {zone_playlist_id}")
                # Store the new playlist ID in the database
                utils.MadBoulderDatabase.setPlaylistItem(zone_code,{"id": zone_playlist_id, "sectors": {}})

        # Add video to the zone playlist
        if zone_playlist_id:
            add_response = utils.channel.addVideoToPlaylist(uploaded_video_id, zone_playlist_id)
            if not add_response:
                print(f"Failed to add video {uploaded_video_id} to playlist {zone_playlist_id}")
            else:
                print(f"Video {uploaded_video_id} added to playlist {zone_playlist_id}")

        # Check if the sector playlist exists, if so add the video
        if sector_code:
            sector_playlist = sector_playlists.get(sector_code)
            if sector_playlist:
                sector_playlist_id = sector_playlist.get("id")
                if sector_playlist_id:
                    add_sector_response = utils.channel.addVideoToPlaylist(uploaded_video_id, sector_playlist_id)
                    if not add_sector_response:
                        print(f"Failed to add video {uploaded_video_id} to sector playlist {sector_playlist_id}")
                    else:
                        print(f"Video {uploaded_video_id} added to sector playlist {sector_playlist_id}")
                else:
                    print(f"Sector playlist ID not found for sector: {sector_code}")
            else:
                print(f"No sector playlist found for sector code: {sector_code}")

        #print("enabling video monetization")
        #utils.channel.enableMonetization(uploaded_video_id) # not working

        return response, publish_time, None

    except Exception as e:
        print(f"Error processing upload: {e}")
        return None, None, str(e)

def generate_success_page(video_id, title, publish_time=None):
    """Generate success page using the upload-completed template"""
    try:
        publish_time_utc = None
        publish_time_utc_iso = None
        if publish_time:
            publish_time_utc = publish_time.strftime('%Y-%m-%d %H:%M:%S')
            publish_time_utc_iso = publish_time.strftime('%Y-%m-%dT%H:%M:%S')

        return render_template('upload-completed.html',
            video_id=video_id,
            title=title,
            publish_time_utc=publish_time_utc,
            publish_time_utc_iso=publish_time_utc_iso
        )
    except Exception as e:
        print(f"Error generating success page: {e}")
        return "<h2>Upload completed, but there was an error generating the success page.</h2>"