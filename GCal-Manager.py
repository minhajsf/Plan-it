import os 
import openai
import json
from dotenv import load_dotenv
from openai import OpenAI
from db import db
from db import Event
from flask import Flask
from flask import request


# USE COMMAND pip install -r requirements.txt
# Then pip freeze > requirements.txt
# To automate the installation of the imports


#Google Imports
import datetime
from datetime import datetime
from tzlocal import get_localzone
import os.path
import urllib3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



def get_events():
    """
    Endpoint for getting all events.
    """
    events = [event.serialize() for event in Event.query.all()]
    return events


SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']

def main():
  
    app = Flask(__name__)
    db_filename = "calendar.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = True

    db.init_app(app)
    with app.app_context():
        db.create_all()

    
    # Get OPENAI_API_KEY from environment variables
    load_dotenv()
    my_api_key = os.getenv('OPENAI_API_KEY')


    # Create an OpenAPI client using the API key
    client = OpenAI(
        api_key=my_api_key,
    )
    # GOOGLE CALENDAR API

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=8080)  # Specify a fixed port here
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)
        
    except:
        # Name of the file to be deleted
        filename = "token.json"
        # Delete the file
        if os.path.exists(filename):
            os.remove(filename)
            print(f"{filename} has been deleted.")
        else:
            print(f"{filename} does not exist.")

        print(f"An error occurred: {error}")
        main()

    # Get event type from user
    eventType = str(input("What type of event would you like to do? (Create, Update, Remove): "))

    # Get the user's request
    prompt = str(input("enter prompt here: "))


    # Insert Event
    if eventType == "Create":

        # PROMPT
        # I have a meeting with Brooke tommorow at noon. It is interview so I need to bring my resume. It's at the Starbucks on 114th and Broadway. Can you add it to my calendar?
        # get localhost time zone
        timeZone = get_localzone()
  
        # get current dateTime in ISO 8601
        current_datetime = datetime.now()

        

        #create a prompt for GPT API
        insert_format_instruction = f"""
        For your response input the following prompt information in the format below as a valid JSON object (start your response at the first left curly brace of the event dictionary) understand that the current time is currently {current_datetime}: 

        {prompt}

        event = {{
        "summary": "insert_title_here",
        "description": "any extra specifications, locations, and descriptions here",
        "start": {{
            "dateTime": " "2015-05-28T09:00:00-07:00",
            "timeZone": "{timeZone}"
        }},
        "end": {{
            "dateTime": "2015-05-28T17:00:00-07:00",
            "timeZone": "{timeZone}"
        }},
        "reminders": {{
            "useDefault": True
        }}
        }}
        """
        # Send ChatGPT the user's prompt and store the response (event dictionary)
        completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": insert_format_instruction}
        ]
        )

        # prints the response from GPT
        print(completion.choices[0].message.content) 

        # Converts response string to a dictionary
        insert_event_dict = json.loads(completion.choices[0].message.content)

        # Creates new event in calendar
        insert_event = service.events().insert(calendarId='primary', body=insert_event_dict).execute()

    
        # Get event id
        insert_event_id = insert_event['id'] 
        # Add to database
        new_event = Event(event_type = eventType,title = insert_event_dict.get("summary"), description = insert_event_dict.get("description"), start = insert_event_dict.get("start").get("dateTime"), end = insert_event_dict.get("end").get("dateTime"), event_id = insert_event_id)
        db.session.add(new_event)
        db.session.commit()
        print(get_events)
        
        print('Event created: %s', insert_event.get('htmlLink'))

    # Update Event
    elif eventType == "Update": 

        # print("Implement soon")

        # get most important word in the event title from prompt
        # search word in database_entry.title

        # print("Is this the event you are looking for? (y/n) ")
        # if not, continue search


        update_format_instruction = None

        # Prepare the update object
        # update = {
        #     'summary': 'Updated Event Title',
        #     'description': 'Updated event description.',
        #     'start': {
        #         'dateTime': '2024-06-25T10:00:00',
        #         'timeZone': 'America/Los_Angeles',
        #     },
        #     'end': {
        #         'dateTime': '2024-06-25T12:00:00',
        #         'timeZone': 'America/Los_Angeles',
        #     },
        #     'location': 'Updated Location',
        # }

        # # Update the event
        # updated_event = service.events().update(
        #     calendarId='primary',
        #     eventId=event_id,
        #     body=update
        # ).execute()

        # print('Event updated: %s' % updated_event.get('htmlLink'))

    # Remove Event
    elif eventType == "Remove":

        print("Implement soon")

    # User inputted incorrect event type
    else:

        print("Please try again with a correct event type (Insert, Update, Remove).")
        exit(1)

#if __name__ == "__main__":
#  main()




    # remove_format_instruction = None

main()

# Google API
# event = {
#   'summary': 'Google I/O 2015',
#   'location': '800 Howard St., San Francisco, CA 94103',
#   'description': 'A chance to hear more about Google\'s developer products.',
#   'start': {
#     'dateTime': '2015-05-28T09:00:00-07:00',
#     'timeZone': 'America/Los_Angeles',
#   },
#   'end': {
#     'dateTime': '2015-05-28T17:00:00-07:00',
#     'timeZone': 'America/Los_Angeles',
#   },
#   'recurrence': [
#     'RRULE:FREQ=DAILY;COUNT=2'
#   ],
#   'attendees': [
#     {'email': 'lpage@example.com'},
#     {'email': 'sbrin@example.com'},
#   ],
#   'reminders': {
#     'useDefault': False,
#     'overrides': [
#       {'method': 'email', 'minutes': 24 * 60},
#       {'method': 'popup', 'minutes': 10},
#     ],
#   },
# }


# Edit Event
# # First retrieve the event from the API.
# event = service.events().get(calendarId='primary', eventId='eventId').execute()

# event['summary'] = 'Appointment at Somewhere'

# updated_event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()

# # Print the updated date.
# print updated_event['updated']

# If modifying these scopes, delete the file token.json.
