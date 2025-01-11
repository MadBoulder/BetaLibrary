import os
from flask_mail import Mail
import utils.emailMessage

class EmailProvider:
    def __init__(self, app):
        self.sender = os.environ['EMAIL_USER']
        self.mailRecipients = os.environ['EMAIL_RECIPIENTS'].split(":")
        self.mailFeedbackRecipients = os.environ['FEEDBACK_MAIL_RECIPIENTS'].split(":")

        app.config.update({
            "MAIL_SERVER": 'smtp.gmail.com',
            "MAIL_PORT": 465,
            "MAIL_USE_TLS": False,
            "MAIL_USE_SSL": True,
            "MAIL_USERNAME": self.sender,
            "MAIL_PASSWORD": os.environ['EMAIL_PASSWORD'],
            "MAIL_RECIPIENTS": self.mailRecipients,
            "FEEDBACK_MAIL_RECIPIENTS": self.mailFeedbackRecipients
        })

        self.mail = Mail(app)


    def send(self, msg, recipients=None):
        try:
             # Add sender and recipients if not already set
            msg.sender = self.sender
            msg.recipients = recipients or self.mailFeedbackRecipients

            self.mail.send(msg)
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            raise
    

    def sendNewVideoBeta(self, properties, filename, file_id):
        msg = utils.emailMessage.newVideoBeta(
            properties=properties,
            filename=filename,
            file_id=file_id
        )
        
        self.send(msg)


    def sendPendingContributor(self, email):
        msg = utils.emailMessage.pendingContributor(
            email=email
        )
        
        self.send(msg)


    def sendContributorApproved(self, email, climber_id):
        msg = utils.emailMessage.contributorApproved(
            climber_id=climber_id
        )
        
        self.send(msg, recipients=[email])

    
    def sendFeedback(self,sender_name, sender_email, feedback_data):
        msg = utils.emailMessage.feedback(
            sender_name=sender_name,
            sender_email=sender_email,
            feedback_data=feedback_data
        )
        
        self.send(msg)

    def sendjoinUs(self, sender_name, sender_email, sender_message, resume):
        msg = utils.emailMessage.joinUs(
            sender_name=sender_name,
            sender_email=sender_email,
            sender_message=sender_message,
            resume=resume
        )
        
        self.send(msg)
        