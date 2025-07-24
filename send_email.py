import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv
import os


class Email:
    def __init__(self, key):
        self.key = key
        
    
    def send_email(self, sender, recipient, email_subject, message):


        # Define email sender and receiver
        email_sender = sender
        email_password = self.key
        email_receiver = recipient

        # Set the subject and body of the email
        subject = email_subject
        body = message

        em = EmailMessage()
        em['From'] = email_sender
        em['To'] = email_receiver
        em['Subject'] = subject
        em.set_content(body)

        # Add SSL (layer of security)
        context = ssl.create_default_context()

        # Log in and send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, email_receiver, em.as_string())


