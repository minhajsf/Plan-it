from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os
import uuid

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Initialize credentials
creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=8080)
    with open("token.json", "w") as token:
        token.write(creds.to_json())

# Build the service
service = build("calendar", "v3", credentials=creds)

def create_google_meet(service, event_data):
    request_id = str(uuid.uuid4())
    event_data['conferenceData'] = {
        'createRequest': {
            'requestId': request_id,
            'conferenceSolutionKey': {
                'type': 'hangoutsMeet'
            },
        }
    }
    event = service.events().insert(
        calendarId='primary',
        body=event_data,
        conferenceDataVersion=1
    ).execute()
    return event

def update_google_meet(service, event_id, updated_event_data):
    event = service.events().patch(
        calendarId='primary',
        eventId=event_id,
        body=updated_event_data,
        conferenceDataVersion=1
    ).execute()
    return event

def delete_google_meet(service, event_id):
    service.events().delete(
        calendarId='primary',
        eventId=event_id
    ).execute()

# Example usage
event_data = {
    'summary': 'Meeting with Google Meet',
    'description': 'Discuss project updates.',
    'start': {
        'dateTime': '2024-07-19T09:00:00-07:00',
        'timeZone': 'America/Los_Angeles',
    },
    'end': {
        'dateTime': '2024-07-19T10:00:00-07:00',
        'timeZone': 'America/Los_Angeles',
    },
    'attendees': [
        {'email': 'attendee1@example.com'},
        {'email': 'attendee2@example.com'}
    ]
}

# Create event with Google Meet link
created_event = create_google_meet(service, event_data)
print(f"Created event: {created_event}")

# The Google Meet link
meet_link = created_event.get('hangoutLink')
print(f"Google Meet Link: {meet_link}")

# Get event ID
event_id = created_event['id']

# Update event
updated_event_data = {
    'summary': 'Updated Meeting with Google Meet',
    'description': 'Discuss project updates and new tasks.',
    'start': {
        'dateTime': '2024-07-19T11:00:00-07:00',
        'timeZone': 'America/Los_Angeles',
    },
    'end': {
        'dateTime': '2024-07-19T12:00:00-07:00',
        'timeZone': 'America/Los_Angeles',
    }
}
updated_event = update_google_meet(service, event_id, updated_event_data)
print(f"Updated event: {updated_event}")

# Delete event
# delete_google_meet(service, event_id)
print(f"Deleted event with ID: {event_id}")
