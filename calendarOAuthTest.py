from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime
import pickle
import os.path

# If modifying these scopes, delete the file token.pickle
SCOPES = ['https://www.googleapis.com/auth/calendar']

def main():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    # Build the service object
    service = build('calendar', 'v3', credentials=creds)
    
    # Call the Calendar API
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get('items', [])
    
    # Print list of calendars
    if not calendars:
        print('No calendars found.')
    else:
        print('Calendars:')
        for calendar in calendars:
            print(f"- {calendar['summary']} (ID: {calendar['id']})")
    
    # Select a calendar ID
    calendar_id = input('Enter the ID of the calendar to add events to: ')
    
    # Example event to be added
    event = {
        'summary': 'Test Event',
        'location': 'Somewhere',
        'description': 'Testing the Google Calendar API',
        'start': {
            'dateTime': '2024-06-26T09:00:00',
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': '2024-06-26T10:00:00',
            'timeZone': 'America/Los_Angeles',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    
    # Insert event
    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f'Event created: {event.get("htmlLink")}')

if __name__ == '__main__':
    main()
