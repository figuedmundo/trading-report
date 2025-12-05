"""
Gmail API Client for sending emails via HTTP (bypassing SMTP ports).
"""
import base64
import os
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailClient:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logger.error(f"Failed to load token.pickle: {e}")

        # If no valid credentials, we need to refresh or generate them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    creds = None

            if not creds:
                # We cannot run the interactive flow inside Docker easily.
                # We expect the token.json (or pickle) to be mounted or present.
                if os.path.exists(self.token_path.replace(".pickle", ".json")):
                     creds = Credentials.from_authorized_user_file(self.token_path.replace(".pickle", ".json"), SCOPES)
                else:
                    raise Exception(
                        f"Valid token not found at {self.token_path}. "
                        "Please run the 'generate_gmail_token.py' script locally to create it."
                    )

            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API service initialized successfully")

    async def send_message(self, to_addr: str, subject: str, html_body: str, text_body: str) -> str:
        """
        Send an email message.
        
        Args:
            to_addr: Recipient email
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content
            
        Returns:
            Message ID string
        """
        if not self.service:
            self._authenticate()

        message = MIMEMultipart('alternative')
        message['to'] = to_addr
        message['from'] = 'me'
        message['subject'] = subject

        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')

        message.attach(part1)
        message.attach(part2)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message}

        try:
            message = self.service.users().messages().send(userId="me", body=body).execute()
            logger.info(f"Email sent via Gmail API. Id: {message['id']}")
            return message['id']
        except Exception as e:
            logger.error(f"An error occurred sending via Gmail API: {e}")
            raise e
