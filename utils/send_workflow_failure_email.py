from flask import Flask
from utils.emailProvider import EmailProvider
from utils.emailMessage import workflow_failure

def send_workflow_failure_email():
    try:
        # Create a minimal Flask app for email configuration
        app = Flask(__name__)
        
        # Initialize email provider
        email_provider = EmailProvider(app)
        
        # Create and send message using our message template
        msg = workflow_failure()
        email_provider.send(msg)
        
    except Exception as e:
        print(f"Failed to send workflow failure email: {e}")

if __name__ == "__main__":
    send_workflow_failure_email() 