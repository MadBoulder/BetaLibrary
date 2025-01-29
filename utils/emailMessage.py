import utils.drive
from flask_mail import Message


def newVideoBeta(properties, filename, file_id):
    fileLink = utils.drive.getFileLink(file_id)
    msg_body_html = f"""
        <p>A new video has been uploaded to MadBoulder.</p>

        <p><strong>Climber:</strong> {properties.climber}</p>
        <p><strong>Email:</strong> {properties.email}</p>
        <p><strong>Name:</strong> {properties.name}</p>
        <p><strong>Grade:</strong> {properties.grade}</p>
        <p><strong>Zone:</strong> {properties.zone}</p>
        <p><strong>Sector:</strong> {properties.sector}</p>
        <p><strong>Notes:</strong> {properties.notes}</p>

        <p><strong>Filename:</strong> {filename}</p>
        <p><strong>Google Drive Link:</strong> <a href="{fileLink}">{fileLink}</a></p>

        <a href="https://madboulder.org/upload-hub?file_id={file_id}" 
            style="display: inline-block; padding: 10px 15px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; text-align: center;"
        >
            Upload to YouTube
        </a>
    """

    return Message(
        subject=f"MadBoulder: New Video Uploaded by {properties.climber}",
        body=f"A new video has been uploaded by {properties.climber}. Please check your email client for HTML content.",  # Fallback text
        html=msg_body_html
    )


def pendingContributor(email):
    msg_body = 'New Contributor Submission pending to approve from user: {}\n\nApprove the request in https://www.madboulder.org/settings/admin/users'.format(email)
    return Message(
        subject="MadBoulder New Contributor Submission",
        body=msg_body
    )


def contributorApproved(climber_id):
    msg_body = 'Your Contributor Submission has been accepted and associated with the following climber id: {}\n\nYou can review it in https://www.madboulder.org/settings/profile'.format(climber_id)       
    return Message(
        subject="Contributor Submission Accepted!",
        body=msg_body
    )


def feedback(sender_name, sender_email, feedback_data):
    msg_body = 'Sender: {} - {}\nMessage: {}'.format(sender_name, sender_email, feedback_data)
    
    return Message(
        subject="madboulder.org feedback",
        body=msg_body
    )


def joinUs(sender_name, sender_email, sender_message, resume):
    msg_body = 'Sender: {} - {}\nMessage: {}'.format(sender_name, sender_email, sender_message)
    msg = Message(
        subject="madboulder.org join us",
        body=msg_body
    )
    msg.attach(resume.filename, 'application/octet-stream', resume.read())

    return msg


def workflow_failure():
    msg_body = """The automatic website update workflow failed.
Please check the GitHub Actions logs at: https://github.com/MadBoulder/BetaLibrary/actions

This could indicate issues with:
- Data updates from YouTube
- Page generation
- Sitemap updates"""

    msg_body_html = """
        <p>The automatic website update workflow failed.</p>
        <p>Please check the GitHub Actions logs at: 
           <a href="https://github.com/MadBoulder/BetaLibrary/actions">GitHub Actions</a>
        </p>
        <p>This could indicate issues with:</p>
        <ul>
            <li>Data updates from YouTube</li>
            <li>Page generation</li>
            <li>Sitemap updates</li>
        </ul>
    """

    msg = Message(
        subject="MadBoulder: Website Update Workflow Failed",
        body=msg_body
    )
    msg.html = msg_body_html

    return msg