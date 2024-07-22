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

SCOPES = ['https://www.googleapis.com/auth/calendar',
               'https://www.googleapis.com/auth/calendar.events',
               'https://www.googleapis.com/auth/meetings.space.created',
               'https://www.googleapis.com/auth/gmail.modify']

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

def google_setup():
    """
    Google Auth & Service.
    """
    def get_google_service():
        if hasattr(g, 'service'):
            return
        creds = None

        # # get current user's id
        # user_id = session.get('user_id')

        # token = Users.query.filter_by(id=user_id).first().token

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
        return build("calendar", "v3", credentials=creds)
    if not hasattr(g, 'service'):
        g.service = get_google_service()  # global used throughout gcal, gmeet, and/or gmail


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

        response = completion.choices[0].message.content

        # Ensure the response is a JSON string
        response = response[response.index("{"):len(response) - response[::-1].index("}")]
        # Fixes the capitalization of True in the response
        response = re.sub(r"\btrue\b", "True", response)
        # Extract and parse the response
        response = json.loads(response)

        # Error handling -- can be removed in prod!

        return response  # response is dict with keys event_type, mode, and title
    except Exception as e:
        print(f"Error processing message: {e}")
        return {"event_type": "unknown", "mode": "unknown"}


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

        response = completion.choices[0].message.content

        # Ensure the response is a JSON string
        response = response[response.index("{"):len(response) - response[::-1].index("}")]
        # Fixes the capitalization of True in the response
        response = re.sub(r"\btrue\b", "True", response)
        # Evaluate to dictionary
        response = eval(response)

        return response
    except Exception as e:
        print(f"Error processing message: {e}")
        return None

def extract_keywords(prompt):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": """You are an assistant who can find a prompt's keywords 
                                        which will be used to query a database. In your response, 
                                        separate keywords with a comma."""},
            {"role": "user", "content": f'This is the prompt: {prompt}'}
        ]
    )
    response = completion.choices[0].message.content

    keywords = [keyword.strip() for keyword in response.split(',')]
    return keywords

def find_event_id(prompt, list):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": """You are an assistant who can determine a specific event based on a prompt. 
                                        Return only the value of the event_id from the event list closest to the prompt. 
                                        If none match return 'invalid'."""},
            {"role": "user", "content": f'This is the prompt: {prompt}. This is the list: {list}'}
        ]
    )
    event_id = completion.choices[0].message.content
    return event_id

def find_meeting_id(prompt, list):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": """You are an assistant who can determine a specific meeting based on a prompt. 
                                        Return only the value of the meet_id from the meeting list closest to the prompt.
                                        If none match return 'invalid'."""},
            {"role": "user", "content": f'This is the prompt: {prompt}. This is the list: {list}'}
        ]
    )
    meeting_id = completion.choices[0].message.content
    return meeting_id

def find_email_id(prompt, list):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": """You are an assistant who can determine a specific email based on a prompt. 
                                        Return only the value of the email_id from the email list closest to the prompt.
                                        If none match return 'invalid'."""},
            {"role": "user", "content": f'This is the prompt: {prompt}. This is the list: {list}'}
        ]
    )
    email_id = completion.choices[0].message.content
    return email_id

@socketio.on('user_prompt')
def handle_user_prompt(prompt):
    print("User prompt recieved: " + prompt, file=sys.stderr)

    # add in prompt to dictionary directly
    # saves time on the gpt call in determine_query_type
    prompt_dictionary = determine_query_type(prompt)
    prompt_dictionary['prompt'] = prompt

    # make the prompt_dictionary a session variable (global to the flask session)
    session['prompt_dictionary'] = prompt_dictionary

    # determine the event type and mode
    event_type = prompt_dictionary['event_type'].lower()
    mode = prompt_dictionary['mode'].lower()

    # TRY eval(f"{event_type}_{mode}()")

    if event_type == "gcal":
        google_setup()
        if mode == "create":
            gcal_create()
        elif mode == "update":
            gcal_update()
        elif mode == "remove":
            gcal_remove()
        else:
            print("Please try again. The program only works for Create, Update, and Remove.", file=sys.stderr)
            exit(1)
    elif event_type == "gmeet":
        google_setup()
        if mode == "create":
            gmeet_create()
        elif mode == "update":
            gmeet_update()
        elif mode == "remove":
            gmeet_remove()
        else:
            print("Please try again. The program only works for Create, Update, and Remove.", file=sys.stderr)
            exit(1)
    elif event_type == "gmail":
        google_setup()
        if mode == "create":
            gmail_create()
        elif mode == "update":
            gmail_update()
        elif mode == "send":
            gmail_send()
        elif mode == "remove":
            print("This is an error. You cannot delete a draft currently")
            #gmail_remove()
        else:
            print("Please try again. The program only works for Create, Update, and Send.", file=sys.stderr)
    else:
        print("Please try again. The program only works for Google Calendar, Google Meet, and Gmail.", file=sys.stderr)


#
# -----------------------------------------------------------------------
# GCAL ROUTES
# -----------------------------------------------------------------------
#


def create_event(service, event_data):
    event = service.events().insert(
        calendarId='primary',
        body=event_data
    ).execute()
    return event


def update_event(service, event_id, updated_event_data):
    updated_event = service.events().update(
        calendarId='primary',
        eventId=event_id,
        body=updated_event_data
    ).execute()
    return updated_event


def remove_event(service, event_id):
    service.events().delete(
        calendarId='primary',
        eventId=event_id
    ).execute()


def format_system_instructions_for_event(query_type_dict: dict, content_dict: dict = None) -> str:
    timeZone = get_localzone()
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    summary = content_dict.get('summary') if content_dict else '<summary_here>'
    description = content_dict.get('description') if content_dict else '<extra specifications, locations, and descriptions here>'
    start = content_dict.get('start') if content_dict else f'start time default {current_datetime}-04:00'
    end = content_dict.get('end') if content_dict else f'end time default {current_datetime}-04:00'

    format_instruction = f"""
    You are an assistant that {query_type_dict.get('mode')}s a Google Calendar event using a sample JSON..
    {'Update only the specified information from user message, leave the rest' if query_type_dict.get('mode') == 'update' else ''}
    Ensure the summary and description are professional and informative. Use default start/end times if none are provided.
    If a start time is provided without an end time, set the end time to 30 minutes after the start time.
    Current_time: {datetime.now()}

    event = {{
        "summary": "{summary}",
        "description": "{description}",
        "start": {{
            "dateTime": "{start}",
            "timeZone": "{timeZone}"
        }},
        "end": {{
            "dateTime": "{end}",
            "timeZone": "{timeZone}"
        }},
        "reminders": {{
            "useDefault": True
        }}
    }}
    """
    return format_instruction.strip()


# Create a calendar event
def gcal_create():

    prompt_dict = session.get('prompt_dictionary')

    # GPT instructions
    format_instruction = format_system_instructions_for_event(prompt_dict)
    
    # GPT response as JSON
    event_data = gpt_format_json(format_instruction, prompt_dict['prompt'])

    event = create_event(g.service, event_data)
    
    new_event = Events(
        user_id=session['user_id'],
        title=event_data.get("summary"),
        description=event_data.get("description"),
        start=event_data.get("start").get("dateTime"),
        end=event_data.get("end").get("dateTime"),
        event_id=event.get("id"),
        event_dictionary=json.dumps(event_data)
    )

    db.session.add(new_event)
    db.session.commit()

    print('Event created! Check your Google Calendar to confirm!\n', file=sys.stderr)


def gcal_update():
    prompt_dict = session.get('prompt_dictionary')
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    #Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    #Limit search to user
    events = Events.query.filter_by(user_id=user_id).all()
    print(Events.query.filter_by(user_id=user_id).first().event_id)
    if not events:
        print("Events not found in db. Try again?")
        return
    
    # Filter events then send to API to find id
    filtered_events = [[{"event_id": event.event_id}, event.event_dictionary] for event in events if any(keyword.lower() in event.title.lower() or keyword.lower() in event.description.lower() for keyword in keywords)]
    print(filtered_events)

    if not filtered_events:
        print("No events found matching the provided keywords.", file=sys.stderr)
        return "No matching events found."

    event_id = find_event_id(user_prompt, filtered_events)
    print(event_id)
    if event_id == 'invalid':
        print("Not enough information, please try again?")
        return
    # query event from database
    #event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    event = Events.query.filter_by(event_id=event_id[1:len(event_id)-1]).first()
    print(event)

    # if not found in db
    if not event:
        print("Event not found in db. Try again?")
        return

    event_content = event.serialize()

    event_id = event.event_id

    # GPT instructions
    format_instruction = format_system_instructions_for_event(prompt_dict, event_content)
  
    # GPT response as JSON
    event_data = gpt_format_json(format_instruction, prompt_dict.get('prompt'))

    updated_event = update_event(g.service, event_id, event_data)

    # event is current entry
    # update the event attributes in the database
    event.title = event_data.get('summary')
    event.description = event_data.get('description')
    event.start = json.dumps(event_data.get('start'))
    event.end = json.dumps(event_data.get('end'))
    event.event_id = updated_event.get('id')
    event.event_dictionary = json.dumps(event_data)

    db.session.commit()
    print('Event created! Check your Google Calendar to confirm!\n', file=sys.stderr)


def gcal_remove():
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    #Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    #Limit search to user
    events = Events.query.filter_by(user_id=user_id).all()
    print(Events.query.filter_by(user_id=user_id).first().event_id)
    if not events:
        print("Events not found in db. Try again?")
        return
    
    # Filter events then send to API to find id
    filtered_events = [[{"event_id": event.event_id}, event.event_dictionary] for event in events if any(keyword.lower() in event.title.lower() or keyword.lower() in event.description.lower() for keyword in keywords)]
    print(filtered_events)

    if not filtered_events:
        print("No events found matching the provided keywords.", file=sys.stderr)
        return "No matching events found."

    event_id = find_event_id(user_prompt, filtered_events)
    print(event_id)
    if event_id == 'invalid':
        print("Not enough information, please try again?")
        return
    # query event from database
    #event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    event = Events.query.filter_by(event_id=event_id[1:len(event_id)-1]).first()
    print(event)

    # remove it from calendar
    remove_event(g.service, event.event_id)

    # remove from our db
    db.session.delete(event)
    db.session.commit()


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


def convert_dict_to_str(attendees):
    return '`'.join(attendee['email'] for attendee in attendees)


def gmeet_create():
    prompt_dict = session.get('prompt_dictionary')

    # No content dict bc create
    instructions = format_system_instructions_for_meeting(prompt_dict)
    event_data = gpt_format_json(instructions, prompt_dict['prompt'])

    event = create_google_meet(g.service, event_data)

    # Create new Meet for our db
    new_meeting = Meets(
        user_id=session['user_id'],
        summary=event_data.get('summary'),
        description=event_data.get('description'),
        start=json.dumps(event_data.get('start')),
        end=json.dumps(event_data.get('end')),
        meet_id=event.get('id'),
        attendees=json.dumps((event_data.get('attendees'))),
        meet_dictionary=json.dumps(event_data)
    )

    db.session.add(new_meeting)
    db.session.commit()
    print("Meeting has been created successfully.")


def gmeet_update():
    prompt_dict = session.get('prompt_dictionary')
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    #Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    #Limit search to user
    meetings = Meets.query.filter_by(user_id=user_id).all()
    print(Meets.query.filter_by(user_id=user_id).first().meet_id)
    if not meetings:
        print("Meetings not found in db. Try again?")
        return
    
    # Filter events then send to API to find id
    filtered_meetings = [[{"meet_id": meeting.meet_id}, meeting.meet_dictionary] for meeting in meetings if any(keyword.lower() in meeting.summary.lower() or keyword.lower() in meeting.description.lower() for keyword in keywords)]
    print(filtered_meetings)

    if not filtered_meetings:
        print("No meetings found matching the provided keywords.", file=sys.stderr)
        return "No matching meeting found."

    meet_id = find_meeting_id(user_prompt, filtered_meetings)
    print(meet_id)
    if meet_id == 'invalid':
        print("Not enough information, please try again?")
        return
    # query event from database
    #event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    meeting = Meets.query.filter_by(meet_id=meet_id.replace('\'', '')).first()
    print(meeting)

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
    # CHECKOUT (why 'title' instead of 'prompt')
    event_data = gpt_format_json(instructions, prompt_dict.get('prompt'))

    event = update_google_meet(g.service, meeting_id, event_data)

    # meeting is current entry
    meeting.summary = event_data.get('summary')
    meeting.description = event_data.get('description')
    meeting.start = json.dumps(event_data.get('start'))
    meeting.end = json.dumps(event_data.get('end'))
    meeting.meet_id = event.get('id')
    meeting.attendees = json.dumps(event_data.get('attendees'))
    meeting.meet_dictionary = json.dumps(event_data)

    db.session.commit()
    print("Meeting updated successfully.")


def gmeet_remove():
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    #Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    #Limit search to user
    meetings = Meets.query.filter_by(user_id=user_id).all()
    print(Meets.query.filter_by(user_id=user_id).first().meet_id)
    if not meetings:
        print("Meetings not found in db. Try again?")
        return
    
    # Filter events then send to API to find id
    filtered_meetings = [[{"meet_id": meeting.meet_id}, meeting.meet_dictionary] for meeting in meetings if any(keyword.lower() in meeting.summary.lower() or keyword.lower() in meeting.description.lower() for keyword in keywords)]
    print(filtered_meetings)

    if not filtered_meetings:
        print("No meetings found matching the provided keywords.", file=sys.stderr)
        return "No matching meeting found."

    meet_id = find_meeting_id(user_prompt, filtered_meetings)
    print(meet_id)
    if meet_id == 'invalid':
        print("Not enough information, please try again?")
        return
    # query event from database
    #event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    meeting_to_remove = Meets.query.filter_by(meet_id=meet_id.replace('\'', '')).first()
    print(meeting_to_remove)

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


# Creates a draft (not message to allow for updating before sending)
def gmail_create():
    prompt_dict = session.get('prompt_dictionary')
    prompt = prompt_dict.get('prompt')

    content_dict = {'sender': f"{get_authenticated_user_email(g.service)}"}
    instructions = format_system_instructions_for_gmail(prompt_dict, content_dict)

    created_email_json = gpt_format_json(instructions, prompt)
    created_email_raw = email_json_to_raw(created_email_json)
    draft = create_gmail_draft(g.service, created_email_raw)

    # save draft in db

    newly_drafted_email = Emails(
        # todo add user id field also
        user_id=session['user_id'],
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
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    #Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    #Limit search to user
    emails = Emails.query.filter_by(user_id=user_id).all()
    print(Emails.query.filter_by(user_id=user_id).first().email_id)
    if not emails:
        print("Emails not found in db. Try again?")
        return
    
    # Filter events then send to API to find id
    filtered_emails = [[{"meet_id": email.email_id}, email.email_dictionary] for email in emails if any(keyword.lower() in email.summary.lower() or keyword.lower() in email.description.lower() for keyword in keywords)]
    print(filtered_emails)

    if not filtered_emails:
        print("No emails found matching the provided keywords.", file=sys.stderr)
        return "No matching emails found."

    email_id = find_email_id(user_prompt, filtered_emails)
    print(email_id)
    if email_id == 'invalid':
        print("Not enough information, please try again?")
        return
    # query event from database
    #event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    draft_to_update = Emails.query.filter_by(email_id=email_id.replace('\'', '')).first()
    print(draft_to_update)

    if not draft_to_update:
        print("No Gmail draft found")
        return

    draft_serialized = draft_to_update.serialize()
    draft_id = draft_to_update.email_id

    instructions = format_system_instructions_for_gmail(prompt_dict, draft_serialized)

    # CHECKOUT (why 'title' instead of 'prompt')
    updated_draft_json = gpt_format_json(instructions, prompt_dict.get('prompt'))
    updated_draft_raw = email_json_to_raw(updated_draft_json)

    updated_draft = update_gmail_draft(g.service, draft_id, updated_draft_raw)

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
        send_gmail_draft(g.service, email_to_send.email_id)

        # remove from db bc its sent, so you can't edit it again anyway
        db.session.delete(email_to_send)
        db.session.commit()


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)