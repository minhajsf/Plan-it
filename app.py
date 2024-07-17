import os
import openai
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
from db import db
from db import Event
from flask import Flask, jsonify
from flask import request


# USE COMMAND pip install -r requirements.txt the first time around
# then pip3 freeze > requirements

# After installing a new import, just do pip3 freeze > requirements.txt
# to automate the installation of the imports


# Google Imports
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
    return json.dumps({"events": events})


SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/calendar.events']


def main():

    # DATABASE SETUP
    app = Flask(__name__)
    db_filename = "calendar.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Print SQLAlchemy INFO logs (True) Silence SQLAlchemy INFO logs (False)
    app.config["SQLALCHEMY_ECHO"] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # CHATGPT API
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
            # Specify a fixed port here
            creds = flow.run_local_server(port=8080)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)
    except Exception:
        # Name of the file to be deleted
        filename = "token.json"
        # Delete the file
        if os.path.exists(filename):
            os.remove(filename)
            print(f"{filename} has been reloaded.")
        else:
            print(f"{filename} does not exist.")
        main()

    # Get event type from user
    eventType = str(input("\nWhat type of event would you like to do? " +
                          "(Create, Update, Remove): "))

    # Create Event
    if eventType == "Create":

        prompt = str(input(f"\nYou are going to Create an Event!" +
                           " Enter your prompt here: \n"))

        # PROMPT
        # get localhost time zone
        timeZone = get_localzone()

        # Get current dateTime in ISO 8601
        current_datetime = datetime.now()

        # Create a prompt for GPT API
        insert_format_instruction = f"""
        For your response input the following prompt information
        in the exact format below. Make sure to start your response
        at the first left curly brace of the event dictionary.
        Understand that the current time is currently.
        Don't change anything about any attributes that the user
        does not give a specification to (including case of
        characters). PLEASE LEAVE True as True not lowercase true.
        {current_datetime}:

        {prompt}

        event = {{
        "summary": "insert_title_here",
        "description": "any extra specifications, locations,
        and descriptions here",
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
        # Send ChatGPT the user's prompt and store the
        # response (event dictionary)
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": insert_format_instruction}
            ]
        )

        # prints the response from GPT
        response = completion.choices[0].message.content

        response = response[response.index("{"):
                            len(response)-response[::-1].index("}")]
        # print(response)

        # Converts response string to a dictionary
        insert_event_dict = eval(response)

        # event description string for printing purposes
        event_description = f'''\nEvent - Title: {insert_event_dict["summary"]}
        \t\tDescription: {insert_event_dict["description"]}
        \nStart Time: {insert_event_dict["start"]["dateTime"]}
        \t\t\tEnd Time: {insert_event_dict["end"]["dateTime"]}\n'''

        # Creates new event in calendar
        insert_event = service.events().insert(
            calendarId='primary',
            body=insert_event_dict).execute()

        # Get event id
        insert_event_id = insert_event['id']
        # Add to database
        with app.app_context():
            # Add to database
            new_event = Event(
                event_type=eventType,
                title=insert_event_dict.get("summary"),
                description=insert_event_dict.get("description"),
                start=insert_event_dict.get("start").get("dateTime"),
                end=insert_event_dict.get("end").get("dateTime"),
                event_id=insert_event_id,
                event_dictionary=response
                )
            db.session.add(new_event)
            db.session.commit()

        print(event_description)
        print('Event created! Check your Google Calendar to confirm!\n')

        return insert_event_dict.get("summary")

    # Update Event
    elif eventType == "Update":

        # get the exact title of event from user
        event_title = str(input('''\nYou are going to Update an event!
                                Which event on your calendar would you
                                like to update? (Exact title): '''))

        # User changes
        event_update = str(input('''What would you like to change
                                 about the event?: '''))

        # perform a query on the database for the title
        with app.app_context():
            event = Event.query.filter_by(title=event_title).first()
            current_event = event.event_dictionary
            current_event_id = event.event_id

        # Update format instruction
        update_format_instruction = f'''
        For your response, update the following format with any
        updated/changed information in the give prompt. Keep the
        attributes the same if no changes are mentioned/if the change
        is redundant (same info as current event).
        Don't change anything about any attributes that the user
        does not give a specification to (including case of
        characters). PLEASE LEAVE True as True not lowercase true.
        prompt = "{event_update}"

        Format of current event:

        {current_event}

        '''

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are a helpful assistant.
                 You will update the fields that need updating."""},
                {"role": "user", "content": update_format_instruction}
            ]
        )

        # prints the response from GPT
        response = completion.choices[0].message.content

        response = response[response.index("{"):
                            len(response)-response[::-1].index("}")]
        # print(response)

        # Converts response string to a dictionary
        updated_event_dict = eval(response)

        event_description = f"""\nUpdated Event:
        \nEvent - Title: {updated_event_dict["summary"]}
        \t\tDescription: {updated_event_dict["description"]}
        \nStart Time: {updated_event_dict["start"]["dateTime"]}
        \t\t\tEnd Time: {updated_event_dict["end"]["dateTime"]}\n"""

        # # Update the event
        updated_event = service.events().update(
            calendarId='primary',
            eventId=current_event_id,
            body=updated_event_dict
        ).execute()

        # Get the event id
        updated_event_id = updated_event['id']
        # Add to database
        with app.app_context():
            # Add to database
            new_event = Event(
                event_type=eventType,
                title=updated_event_dict.get("summary"),
                description=updated_event_dict.get("description"),
                start=updated_event_dict.get("start").get("dateTime"),
                end=updated_event_dict.get("end").get("dateTime"),

                # leave the event_id as the the Create event id.
                # This is to keep track of which event you updated
                event_id=current_event_id,
                event_dictionary=response
            )
            db.session.add(new_event)
            db.session.commit()

        print(event_description)
        print('Event Updated! Check your Google Calendar to confirm!\n')

        return updated_event["summary"]
        # print('Event updated: %s' % updated_event.get('htmlLink'))

    # Remove Event
    elif eventType == "Remove":

        # get the exact title of event from user
        event_title = str(input('''\nYou are going to Remove an event!
                                Which event on your calendar would you like
                                to remove? (Exact title): '''))

        # perform a query on the database for the title
        with app.app_context():
            event = Event.query.filter_by(title=event_title).first()
            current_event = event.event_dictionary
            current_event_id = event.event_id

        deleted_event_dict = eval(current_event)

        current_event_description = f"""
        Event - Title: {deleted_event_dict["summary"]}
        \t\tDescription: {deleted_event_dict["description"]}
        \nStart Time: {deleted_event_dict["start"]["dateTime"]}
        \t\t\tEnd Time: {deleted_event_dict["end"]["dateTime"]}\n"""

        confirmation = str(input(f"""Event To-Be-Deleted: \n
                                 {current_event_description}
                                 Are you sure you want this event deleted?
                                 (y/n): """))

        if confirmation == "y":

            service.events().delete(
                calendarId='primary',
                eventId=current_event_id
            ).execute()

            with app.app_context():
                # Add to database
                new_event = Event(
                    event_type=eventType,
                    title=deleted_event_dict.get("summary"),
                    description=deleted_event_dict.get("description"),
                    start=deleted_event_dict.get("start").get("dateTime"),
                    end=deleted_event_dict.get("end").get("dateTime"),

                    # leave the event_id as the the Create event id.
                    # This is to keep track of which event you deleted
                    event_id=current_event_id,
                    event_dictionary=current_event
                )
                db.session.add(new_event)
                db.session.commit()

            return deleted_event_dict.get("summary")
        elif confirmation == "n":
            print("""\nOk. Please try again with the exact event title that you
                  want removed.""")
            return None
        else:
            print("\nYou have inputed an unsupported response. Please try" +
                  "again")
            return None
    # User inputted incorrect event type
    else:

        print("Please try again with a correct event type (Insert, Update," +
              "Remove).")
        exit(1)


if __name__ == "__main__":
    main()
