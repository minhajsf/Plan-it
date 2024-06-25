import datetime
import os.path
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly", 'https://www.googleapis.com/auth/calendar']

logging.basicConfig(level=logging.DEBUG)

def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        logging.debug("Loading credentials from token.json")
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.debug("Refreshing credentials")
            creds.refresh(Request())
        else:
            logging.debug("Initiating authorization flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES,

                # CONTINUE HEREEEEEEEEE
                redirect_uri='http://localhost:' + {port_number} + '/oauth2callback'
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            logging.debug("Saving credentials to token.json")
            token.write(creds.to_json())

    try:
        logging.debug("Building Google Calendar API service")
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        logging.debug(f"Fetching events starting from {now}")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            logging.debug("No upcoming events found.")
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()
