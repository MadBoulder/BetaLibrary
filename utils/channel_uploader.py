from datetime import datetime
from flask import jsonify
import utils.channel
import utils.MadBoulderDatabase

def process_channel_upload(title, description, tags, scheduled_time, zone_code, sector_code, video_stream):
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
            tags=tags if isinstance(tags, list) else tags.split(','),
            privacy_status='private',
            publish_time=publish_time
        )

        uploaded_video_id = response['id']
        print("video uploaded to channel")
        
        # Add to playlists
        print(f"adding video to playlist {zone_code}")
        playlists = utils.MadBoulderDatabase.getPlaylistData(zone_code)
        zone_playlist_id = playlists.get("id")
        sector_playlists = playlists.get("sectors", {})

        if zone_playlist_id:
            utils.channel.addVideoToPlaylist(uploaded_video_id, zone_playlist_id)

        if sector_code in sector_playlists:
            print("adding video to sector playlist")
            sector_playlist_id = sector_playlists[sector_code]["id"]
            utils.channel.addVideoToPlaylist(uploaded_video_id, sector_playlist_id)

        print("enabling video monetization")
        utils.channel.enableMonetization(uploaded_video_id)

        return response, publish_time, None

    except Exception as e:
        print(f"Error processing upload: {e}")
        error_response = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        return None, None, error_response

def generate_success_page(video_id, title, publish_time=None):
    """Generate success page HTML with video details"""
    try:
        youtube_url = f"https://studio.youtube.com/video/{video_id}/edit"
        success_html = f"""
        <h2>Video Upload Successful!</h2>
        <p>Your video "{title}" has been uploaded to YouTube.</p>
        """
        
        if publish_time:
            # Format datetime to ISO format for JavaScript
            utc_time = publish_time.strftime('%Y-%m-%dT%H:%M:%S')
            success_html += f"""
            <script>
                function formatMadridTime(utcString) {{
                    const utcDate = new Date(utcString + 'Z');
                    return new Intl.DateTimeFormat('en-GB', {{
                        timeZone: 'Europe/Madrid',
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        hour12: false
                    }}).format(utcDate);
                }}
                
                document.write(`
                    <p>The video will be published at: ${{formatMadridTime("{utc_time}")}} (Madrid time)</p>
                `);
            </script>
            <noscript>
                <p>The video will be published at: {publish_time} (UTC)</p>
            </noscript>
            """
        
        success_html += f"""
        <p>Continue the edition in Youtube Studio:</p>
        <a href="{youtube_url}">{title}</a>
        """
        
        return success_html
        
    except Exception as e:
        print(f"Error generating success page: {e}")
        return "<h2>Upload completed, but there was an error generating the success page.</h2>"