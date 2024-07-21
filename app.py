import os
import json
import sys
import re
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
import uuid
import base64
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



# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plan-it.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False
migrate = Migrate(app, db)
db.init_app(app)
with app.app_context():
    db.create_all()


# ChatGPT API Setup
client = OpenAI(
    api_key=OPENAI_API_KEY,
)

GCAL_SCOPES = ['https://www.googleapis.com/auth/calendar',
               'https://www.googleapis.com/auth/calendar.events']

GMEET_SCOPES = ['https://www.googleapis.com/auth/meetings.space.created']

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

@app.route('/')
def index():
    print("'index' route hit", file=sys.stderr)
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


def determine_query_type(message: str):
    try:
        # Ideally we remove the creation part and make it global itf
        client = OpenAI(api_key=OPENAI_API_KEY)
        # Make API request
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system",
                 "content": """You are an assistant that determines if a message is related to either Google Calendar,
                            Google Meet, or Gmail. Return a json response as {'event_type': , 
                            'mode': , 'title': } where type is gcal, gmeet, or gmail. If the type is gcal or gmeet, the mode
                            can be create, update, or remove. For email, the mode can be create, update, or send. Add 
                            the subject to title field if needed"""},
                {"role": "user", "content": f"The message is the following: {message}"}
            ]
        )
        response = json.loads(completion.choices[0].message.content)

        # Error handling -- can be removed in prod!
        print(type(response))
        print(response)

        return response  # response is dict with keys event_type, mode, and title
    except Exception as e:
        print(f"Error processing message: {e}")
        return {"event_type": "unknown", "mode": "unknown"}


@socketio.on('user_prompt')
def handle_user_prompt(prompt):
    print("User prompt recieved: " + prompt, file=sys.stderr)

    # add in prompt to dictionary directly
    # saves time on the gpt call in determine_query_type
    prompt_dictionary = determine_query_type(prompt)
    prompt_dictionary['prompt'] = prompt

    # make the prompt_dictionary a session variable (global to the flask session)
    session['prompt_dictionary'] = prompt_dictionary

    if prompt_dictionary['event_type'].lower() == "gcal":

        # Setup GCal API
        # initialize events.db (Events table)
        gcal()

        # mode = prompt_dictionary['mode'].lower()
        # eval(f"gcal_{mode}()")
        if prompt_dictionary['mode'].lower() == "create":
            gcal_create()
        elif prompt_dictionary['mode'].lower() == "update":
            gcal_update()
        elif prompt_dictionary['mode'].lower() == "remove":
            gcal_remove()
        else:
            print("Please try again. The program only works for Create, Update, and Remove.", file=sys.stderr)
            exit(1)
    elif prompt_dictionary['event_type'].lower() == "gmeet":
        gmeet_setup()
        if prompt_dictionary['mode'].lower() == "create":
            gmeet_create()
        elif prompt_dictionary['mode'].lower() == "update":
            gmeet_update()
        elif prompt_dictionary['mode'].lower() == "remove":
            gmeet_remove()
        else:
            print("Please try again. The program only works for Create, Update, and Remove.", file=sys.stderr)
            exit(1)
    elif prompt_dictionary['event_type'].lower() == "gmail":
        gmail_setup()
        if prompt_dictionary['mode'].lower() == "create":
            gmail_create()
        elif prompt_dictionary['mode'].lower() == "update":
            gmail_update()
        elif prompt_dictionary['mode'].lower() == "send":
            gmail_send()
        elif prompt_dictionary['mode'].lower() == "remove":
            print("This is an error. You cannot delete a draft currently")
            raise NotImplementedError  # todo if time
        else:
            print("Please try again. The program only works for Create, Update, and Remove.", file=sys.stderr)
            exit(1)
        return 1
    else:
        print("Please try again. The program only works for Google Calendar, Google Meet, and Gmail.", file=sys.stderr)
        exit(1)
    #with app.app_context():
    #    return redirect(url_for(prompt_type))
    # emit('server_response', f'Server received: {message}', room=request.sid)


#
# -----------------------------------------------------------------------
# GCAL ROUTES
# -----------------------------------------------------------------------
#

def gcal():
    """
    Endpoint for Google Calendar.
    """

    print("'gcal' route hit", file=sys.stderr)


    # CHATGPT API
    # Get OPENAI_API_KEY from environment variables
    load_dotenv()
    my_api_key = os.getenv('OPENAI_API_KEY')

    # Create an OpenAPI client using the API key
    g.client = OpenAI(
        api_key=my_api_key,
    )


    # GOOGLE CALENDAR API
    creds = None
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

# Create a calendar event
def gcal_create():
    print("'gcal_create' route hit", file=sys.stderr)

    prompt = session['prompt_dictionary']['prompt']
    title = session['prompt_dictionary']['title']

    # PROMPT
    # get localhost time zone
    timeZone = get_localzone()

    # Get current dateTime in ISO 8601
    current_datetime = datetime.now()

    # Create a prompt for GPT API
    insert_format_instruction = f"""
    Understand that the current date is {current_datetime}.
    Based on the following prompt, populate the JSON format below.
    Don't change anything about any attributes that the user
    does not give a specification to. Prompt: {prompt} JSON format:

    event = {{
    "summary": "{title}",
    "description": "<insert_description_specifications_here>",
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
        response_format={"type": "json_object"},  # response is ALWAYS json, include json in prompt to work
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": insert_format_instruction}
        ]
    )

    # prints the response from GPT
    response = completion.choices[0].message.content

    response = response[response.index("{"):
                        len(response) - response[::-1].index("}")]


    # Fixes the capitalization of True in the response
    response = re.sub(r"\btrue\b", "True", response)

    # Converts response string to a dictionary
    insert_event_dict = eval(response)

    # event description string for printing purposes
    event_description = f'''\nEvent: 
    \nTitle: {insert_event_dict["summary"]}
    \nDescription: {insert_event_dict["description"]}
    \nStart Time: {insert_event_dict["start"]["dateTime"]}
    \nEnd Time: {insert_event_dict["end"]["dateTime"]}\n'''

    # Creates new event in calendar
    insert_event = getattr(g, 'service').events().insert(
        calendarId='primary',
        body=insert_event_dict).execute()

    # Get event id
    insert_event_id = insert_event['id']
    # Add to database
    # Add to database
    new_event = Events(
        user_id=session['user_id'],
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

    print(event_description, file=sys.stderr)
    print('Event created! Check your Google Calendar to confirm!\n', file=sys.stderr)

    return insert_event_dict["summary"]


# Update a calendar event
def gcal_update():

    print("'gcal_update' route hit", file=sys.stderr)

    event_title = session['prompt_dictionary']['title']
    event_update = session['prompt_dictionary']['prompt']

    event = Events.query.filter_by(title=event_title).first()
    current_event = event.event_dictionary
    current_event_id = event.event_id

    current_datetime = datetime.now()

    # Update format instruction
    update_format_instruction = f'''
    Understand that the current date is {current_datetime}.
    Based on the following prompt, update the values of the following JSON format 
    with any updates/changes. Keep the attribute values the same including the date/time
    if no changes are mentioned within the prompt or if the change is redundant 
    (same info as current event). Prompt: "{event_update}"

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
    
    # Fixes the capitalization of True in the response
    response = re.sub(r"\btrue\b", "True", response)

    # Converts response string to a dictionary
    updated_event_dict = eval(response)

    updated_event_description = f"""\nUpdated Event:
    \nEvent - Title: {updated_event_dict["summary"]}
    \nDescription: {updated_event_dict["description"]}
    \nStart Time: {updated_event_dict["start"]["dateTime"]}
    \nEnd Time: {updated_event_dict["end"]["dateTime"]}\n"""

    # # Update the event
    updated_event = getattr(g, 'service').events().update(
        calendarId='primary',
        eventId=current_event_id,
        body=updated_event_dict
    ).execute()

    # Add to database
    new_event = Events(
        user_id=session['user_id'],
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

    print(updated_event_description, file=sys.stderr)
    print('Event Updated! Check your Google Calendar to confirm!\n', file=sys.stderr)

    return updated_event["summary"]


# Remove a calendar event
def gcal_remove():

    print("'gcal_remove' route hit", file=sys.stderr)

    event_title = session['prompt_dictionary']['title']

    # perform a query on the database for the title
    event = Events.query.filter_by(title=event_title).first()

    if event:
        print(f"Event found: {event_title}", file=sys.stderr)
    else:
        print(f"Event not found: {event_title}", file=sys.stderr)
        exit(1)
    
    current_event = event.event_dictionary
    current_event_id = event.event_id

    deleted_event_dict = eval(current_event)

    deleted_event_description = f"""Event: \n
    \nTitle: {deleted_event_dict["summary"]}
    \nDescription: {deleted_event_dict["description"]}
    \nStart Time: {deleted_event_dict["start"]["dateTime"]}
    \nEnd Time: {deleted_event_dict["end"]["dateTime"]}\n"""

    #
    #
    #ADD SOME WAY TO WARN THE USER THAT THEY ARE DELETING AN EVENT (y/n)
    #
    #

    getattr(g, 'service').events().delete(
        calendarId='primary',
        eventId=current_event_id
    ).execute()

    # Add to database
    new_event = Events(
        user_id=session['user_id'],
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

    print(deleted_event_description, file=sys.stderr)
    print('Event Deleted! Check your Google Calendar to confirm!\n', file=sys.stderr)

    return deleted_event_dict["summary"]


#
# -----------------------------------------------------------------------
# GMEET ROUTES
# -----------------------------------------------------------------------
#
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


def format_system_instructions_for_meeting(query_type_dict: dict, content_dict: dict = None) -> str:
    curr_time_zone = str(get_localzone())

    summary = content_dict.get('summary') if content_dict else '<summary_here>'
    description = content_dict.get(
        'description') if content_dict else 'extra specifications, locations, and descriptions'
    start = content_dict.get('start') if content_dict else 'start time example format <2015-05-28T09:00:00-07:00>'
    end = content_dict.get('end') if content_dict else 'end time example format <2015-05-28T17:00:00-07:00>'
    attendees = content_dict.get('attendees',
                                 []) if content_dict else []  # List of attendees or an empty list if not provided

    # Format attendees
    if attendees:
        attendees_list = [
            {"email": email} for email in attendees
        ]
    else:
        attendees_list = [{"email": "example@gmail.com"}]

    instructions = f"""
    You are an assistant that {query_type_dict.get('mode')}s a Google Meeting using a sample JSON.
    {'Update only the specified information from user message, leave the rest' if query_type_dict.get('mode') == 'update' else ''}
    Ensure the summary and description are professional and informative.
    Current_time: {datetime.now()}
    event = {{
        "summary": "{summary}",
        "description": "{description}",
        "start": {{
            "dateTime": "{start}",
            "timeZone": "{curr_time_zone}"
        }},
        "end": {{
            "dateTime": "{end}",
            "timeZone": "{curr_time_zone}"
        }},
        "attendees": {attendees_list}, 
        "reminders": {{
            "useDefault": True
        }}
    }}
    """
    return instructions.strip()


def gpt_format_json(system_instructions: str, input_string: str):
    try:
        # Make API request

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system",
                 "content": system_instructions},
                {"role": "user", "content": f"String from user: {input_string}"}
            ]
        )

        # Extract and parse the response
        response = json.loads(completion.choices[0].message.content)
        print(type(response))
        print(response)
        return response
    except Exception as e:
        print(f"Error processing message: {e}")
        return None


def convert_dict_to_str(attendees):
    return '`'.join(attendee['email'] for attendee in attendees)


@app.route('/gmeet', methods=['GET'])
def gmeet_setup():
    def get_google_service():
        if hasattr(g, 'service'):
            return
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", GCAL_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", GCAL_SCOPES
                )
                creds = flow.run_local_server(port=8080)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)
    if not hasattr(g, 'service'):
        g.service = get_google_service()  # global used throughout the gmeet section


def gmeet_create():
    prompt_dict = session.get('prompt_dictionary')

    # No content dict bc create
    instructions = format_system_instructions_for_meeting(prompt_dict)
    event_data = gpt_format_json(instructions, prompt_dict)

    event = create_google_meet(g.service, event_data)

    # Create new Meet for our db
    new_meeting = Meets(
        summary=event_data.get('summary'),
        description=event_data.get('description'),
        start=event_data.get('start'),
        end=event_data.get('end'),
        meet_id=event.get('id'),
        attendees=convert_dict_to_str(event_data.get('attendees')),
        meet_dictionary=json.dumps(event_data)
    )

    db.session.add(new_meeting)
    db.session.commit()
    print("Meeting has been created successfully.")


def gmeet_update():
    prompt_dict = session.get('prompt_dictionary')

    # query from database and set vars to update josn
    meeting = Meets.query.filter_by(summary=prompt_dict.get('title')).first()

    # if not found in db
    if not meeting:
        print("Meeting not found in db. Try again?")
        return

    meeting_content = meeting.serialize()

    # backtick convention for splitting attendees column
    meeting_content['attendees'] = meeting_content['attendees'].split('`')
    meeting_id = meeting.meet_id

    # instructions if either update or create
    instructions = format_system_instructions_for_meeting(prompt_dict, meeting_content)

    # formatted response from gpt --> can be passed directly into create or remove
    event_data = gpt_format_json(instructions, prompt_dict.get('title'))

    event = update_google_meet(g.service, meeting_id, event_data)

    # meeting is current entry
    meeting.summary = event_data.get('summary')
    meeting.description = event_data.get('description')
    meeting.start = event_data.get('start')
    meeting.end = event_data.get('end')
    meeting.meet_id = event.get('id')
    meeting.attendees = convert_dict_to_str(event_data.get('attendees'))
    meeting.meet_dictionary = json.dumps(event_data)

    db.session.commit()
    print("Meeting updated successfully.")


def gmeet_remove():
    summary_of_meeting = session['prompt_dictionary']['title']

    # find entity to delete
    meeting_to_remove = Meets.query.filter_by(summary=summary_of_meeting).first()

    # remove it from calendar
    delete_google_meet(g.service, meeting_to_remove.meet_id)

    # remove from our db
    db.session.delete(meeting_to_remove)
    db.session.commit()

#
# -----------------------------------------------------------------------
# GMAIL ROUTES
# -----------------------------------------------------------------------
#
def get_authenticated_user_email(service):
    try:
        profile = service.users().getProfile(userId='me').execute()
        return profile['emailAddress']
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def email_json_to_raw(email_json):
    from_field = email_json['from'][0]  # Assuming `from_list` has a single email
    to_field = ', '.join(email_json['to'])
    cc_field = ', '.join(email_json['cc']) if email_json['cc'] else ''

    raw_email = f"""From: {from_field}
To: {to_field}
Cc: {cc_field}
Subject: {email_json['subject']}
Content-Type: text/plain; charset="UTF-8"

{email_json['body']}
"""
    return raw_email



def format_system_instructions_for_gmail(query_type_dict: dict, content_dict: dict = None) -> str:
    recipient = content_dict.get('to') if content_dict else '<recipient_email>'
    subject = content_dict.get('subject') if content_dict else '<email_subject>'
    body = content_dict.get('body') if content_dict else '<email_body>'
    sender = content_dict.get('from', 'noreply@example.com') if content_dict else 'noreply@example.com'
    cc = content_dict.get('cc', []) if content_dict else []

    instructions = f"""
    You are an assistant that {query_type_dict.get('mode', 'create')}s an email using a sample JSON format.
    Leave unspecified attributes unchanged. Ensure the subject and body are professional and informative.
    Current_time: {datetime.now()}
    email = {{
        "from": "{sender}",
        "to": {recipient},
        "cc": {cc},
        "subject": "{subject}",
        "body": "{body}"
    }}
    """
    print(type(instructions))
    print(instructions)
    return instructions.strip()


def create_gmail_draft(service, message_body_raw):
    try:
        message = {
            'message': {
                'raw': base64.urlsafe_b64encode(message_body_raw.encode('utf-8')).decode('utf-8')
            }
        }
        draft = service.users().drafts().create(userId='me', body=message).execute()
        return draft
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def update_gmail_draft(service, draft_id, updated_message_body_raw):
    try:
        message = {
            'message': {
                'raw': base64.urlsafe_b64encode(updated_message_body_raw.encode('utf-8')).decode('utf-8')
            }
        }
        draft = service.users().drafts().update(userId='me', id=draft_id, body=message).execute()
        return draft
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def send_gmail_draft(service, draft_id):
    try:
        # draft =
        service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
        print("Draft sent successfully")
        # return draft
    except Exception as e:
        print(f"An error occurred: {e}")

@app.route('/gmail', methods=['GET'])
def gmail_setup():
    """
    Endpoint for Gmail.
    """
    def get_gmail_service():
        if hasattr(g, 'service'):
            return
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", GMAIL_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", GCAL_SCOPES
                )
                creds = flow.run_local_server(port=8080)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)
    if not hasattr(g, 'gmail_service'):
        g.gmail_service = get_gmail_service() # global specific to session


# Creates a draft (not message to allow for updating before sending)
def gmail_create():
    prompt_dict = session.get('prompt_dictionary')
    prompt = prompt_dict.get('prompt')

    content_dict = {'sender': f"{get_authenticated_user_email(g.gmail_service)}"}
    instructions = format_system_instructions_for_gmail(prompt_dict, content_dict)

    created_email_json = gpt_format_json(instructions, prompt)
    created_email_raw = email_json_to_raw(created_email_json)
    draft = create_gmail_draft(g.gmail_service, created_email_raw)

    # save draft in db

    newly_drafted_email = Emails(
        # todo add user id field also
        subject=created_email_json['subject'],
        body=created_email_json['body'],
        sender=created_email_json['from'],
        cc=created_email_json['cc'],
        to=created_email_json['to'],
        email_id=draft.get('id'),
        email_dictionary=json.dumps(created_email_json),
    )
    db.session.add(newly_drafted_email)
    db.session.commit()
    print("Gmail draft created successfully")



# Updates a draft
def gmail_update():
    prompt_dict = session.get('prompt_dictionary')

    draft_to_update = Emails.query.filter_by(subject=prompt_dict.get('title')).first()

    if not draft_to_update:
        print("No Gmail draft found")
        return

    draft_serialized = draft_to_update.serialize()
    draft_id = draft_to_update.email_id

    instructions = format_system_instructions_for_gmail(prompt_dict, draft_serialized)

    updated_draft_json = gpt_format_json(instructions, prompt_dict.get('title'))
    updated_draft_raw = email_json_to_raw(updated_draft_json)

    updated_draft = update_gmail_draft(g.gmail_service, draft_id, updated_draft_raw)

    draft_to_update.subject = updated_draft_json.get('subject')
    draft_to_update.body = updated_draft_json.get('body')
    draft_to_update.cc = updated_draft_json.get('cc')
    draft_to_update.to = updated_draft_json.get('to')
    draft_to_update.email_dictionary = json.dumps(updated_draft_json)
    # from draft itself not json
    draft_to_update.email_id = updated_draft.get('id')
    # I chose to not allow the sender to be updated bc that doesnt make sense

    db.session.commit()
    print("Email draft updated successfully")


# Sends a draft
def gmail_send():
    # title is key of subject in determine_query_type
    subject_of_email = session['prompt_dictionary']['title']
    email_to_send = Emails.query.filter_by(subject=subject_of_email).first()

    if email_to_send:
        send_gmail_draft(g.gmail_service, email_to_send.email_id)

        # remove from db bc its sent, so you can't edit it again anyway
        db.session.delete(email_to_send)
        db.session.commit()


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
