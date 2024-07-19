import os
import json
from flask import Flask, jsonify, render_template, url_for, flash, redirect, request, session, g, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_behind_proxy import FlaskBehindProxy
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import socketio
from dotenv import load_dotenv
from openai import OpenAI
from db import db, Users, Events, Meets, Emails


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
from google.apps import meet_v2


# Flask App setup
app = Flask(__name__)
socketio = SocketIO(app)
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
proxied = FlaskBehindProxy(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')

# ChatGPT API Setup
client = OpenAI(
    api_key=OPENAI_API_KEY,
)

GCAL_SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/calendar.events']

GMEET_SCOPES = ['https://www.googleapis.com/auth/meetings.space.created']

@app.route('/')
def index():
    return render_template('ioExample.html')


@socketio.on('connect')
def handle_new_connection():
    print('Client connected.')
    session['socket_id'] = request.sid
    join_room(session['socket_id'])
    emit('status', {'msg': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    leave_room(session['socket_id'])  # Leave room when client disconnects
    session.clear()


def determine_query_type(message):
    # this can be modified so that we only make one instance per session itf
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Determine if the following message is related to either Gmail, Google Meet, or a "
                                        "Google Calendar event. Once you have determined that, return 'gcal', 'gmeet', "
                                        "or 'gmail' in that exact spelling and in lowercase."}
        ]
    )
    response = completion.choices[0].message.content
    return response

@socketio.on('user_prompt')
def handle_user_prompt(prompt):
    prompt_type = determine_query_type(prompt)
    redirect(url_for(prompt_type))
    # emit('server_response', f'Server received: {message}', room=request.sid)



#
# -----------------------------------------------------------------------
# GCAL ROUTES
# -----------------------------------------------------------------------
#

@app.route('/gcal', methods=['GET'])
def gcal():

    """
    Endpoint for Google Calendar.
    """

    # CALENDAR DATABASE SETUP
    db_filename = "events.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Print SQLAlchemy INFO logs (True) Silence SQLAlchemy INFO logs (False)
    app.config["SQLALCHEMY_ECHO"] = False

    db.init_app(app)
    
    db.create_all()

    # GOOGLE CALENDAR API
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GCAL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", GCAL_SCOPES
            )
            # Specify a fixed port here
            creds = flow.run_local_server(port=8080)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        g.service = build("calendar", "v3", credentials=creds)
    except Exception:
        # Name of the file to be deleted
        filename = "token.json"
        # Delete the file
        if os.path.exists(filename):
            os.remove(filename)
            print(f"{filename} has been reloaded.")
        else:
            print(f"{filename} does not exist.")
        gcal()

    # Get event type from user
    eventType = str(request.args.get('event_type'))

    # Create Event
    if eventType == "Create":
        redirect(url_for('gcal_create'))
    elif eventType == "Update":
        redirect(url_for('gcal_update'))
    elif eventType == "Remove":
        redirect(url_for('gcal_remove'))
    else:
        print("""Please try again with a correct event type (Insert, Update, 
              Remove).""")
        exit(1)


# Create a calendar event
@app.route('/gcal_create', methods=['POST'])
def gcal_create():

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
                        len(response) - response[::-1].index("}")]
    # print(response)

    # Converts response string to a dictionary
    insert_event_dict = eval(response)

    # event description string for printing purposes
    event_description = f'''\nEvent - Title: {insert_event_dict["summary"]}
    \t\tDescription: {insert_event_dict["description"]}
    \nStart Time: {insert_event_dict["start"]["dateTime"]}
    \t\t\tEnd Time: {insert_event_dict["end"]["dateTime"]}\n'''

    # Creates new event in calendar
    insert_event = getattr(g, 'service').events().insert(
        calendarId='primary',
        body=insert_event_dict).execute()

    # Get event id
    insert_event_id = insert_event['id']
    # Add to database
    # Add to database
    new_event = Events(
        # user_id
        user_id=1,
        event_type="Create",
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


# Update a calendar event
@app.route('/gcal_update', methods=['POST'])
def gcal_update():
    # get the exact title of event from user
    event_title = str(input("""\nYou are going to Update an event!
                                Which event on your calendar would you
                                like to update? (Exact title): """))
    # User changes
    event_update = str(input('''What would you like to change
                                about the event?: '''))

    event = Events.query.filter_by(title=event_title).first()
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
                        len(response) - response[::-1].index("}")]
    # print(response)

    # Converts response string to a dictionary
    updated_event_dict = eval(response)

    event_description = f"""\nUpdated Event:
    \nEvent - Title: {updated_event_dict["summary"]}
    \t\tDescription: {updated_event_dict["description"]}
    \nStart Time: {updated_event_dict["start"]["dateTime"]}
    \t\t\tEnd Time: {updated_event_dict["end"]["dateTime"]}\n"""

    # # Update the event
    updated_event = getattr(g, 'service').events().update(
        calendarId='primary',
        eventId=current_event_id,
        body=updated_event_dict
    ).execute()

    # Get the event id
    updated_event_id = updated_event['id']
    # Add to database
    # Add to database
    new_event = Events(
        user_id=1,
        event_type="Update",
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


# Remove a calendar event
@app.route('/gcal_remove', methods=['POST'])
def gcal_remove():
    # get the exact title of event from user
    event_title = str(input('''\nYou are going to Remove an event!
                            Which event on your calendar would you like
                            to remove? (Exact title): '''))

    # perform a query on the database for the title
    event = Events.query.filter_by(title=event_title).first()
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

        getattr(g, 'service').events().delete(
            calendarId='primary',
            eventId=current_event_id
        ).execute()

        # Add to database
        new_event = Events(
            user_id=1,
            event_type="Remove",
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


#
# -----------------------------------------------------------------------
# GMEET ROUTES
# -----------------------------------------------------------------------
#

@app.route('/gmeet', methods=['GET'])
def gmeet():
    """
    Endpoint for Google Meet.
    """

    # MEETS DATABASE SETUP
    db_filename = "meets.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Print SQLAlchemy INFO logs (True) Silence SQLAlchemy INFO logs (False)
    app.config["SQLALCHEMY_ECHO"] = False

    db.init_app(app)
    
    db.create_all()

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', GMEET_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', GMEET_SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        client = meet_v2.SpacesServiceClient(credentials=creds)
        request = meet_v2.CreateSpaceRequest()
        response = client.create_space(request=request)
        print(f'Space created: {response.meeting_uri}')
    except Exception as error:
        # TODO(developer) - Handle errors from Meet API.
        print(f'An error occurred: {error}')

    return "Google Meet"

@app.route('/gmeet_create', methods=['GET'])
def gmeet_create():
    """
    new_meet = Meets(
        user_id=1,
        event_type="Create",

    """
    return "Google Meet Create"
@app.route('/gmeet_update', methods=['GET'])
def gmeet_update():
    return "Google Meet Update"
@app.route('/gmeet_remove', methods=['GET'])
def gmeet_remove():
    return "Google Meet Remove"


#
# -----------------------------------------------------------------------
# GMAIL ROUTES
# -----------------------------------------------------------------------
#

@app.route('/gmail', methods=['GET'])
def gmail():
    """
    Endpoint for Gmail.
    """

    # EMAILS DATABASE SETUP
    db_filename = "emails.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Print SQLAlchemy INFO logs (True) Silence SQLAlchemy INFO logs (False)
    app.config["SQLALCHEMY_ECHO"] = False

    db.init_app(app)
    
    db.create_all()

    return "Gmail"

# Creates a draft (not message to allow for updating before sending)
@app.route('/gmail_create', methods=['GET'])
def gmail_create():
    return "Gmail Create"
# Updates a draft
@app.route('/gmail_update', methods=['GET'])
def gmail_update():
    return "Gmail Update"
# Sends a draft
@app.route('/gmail_send', methods=['GET'])
def gmail_send():
    return "Gmail Send"


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)