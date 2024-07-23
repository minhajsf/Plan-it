import os
import json
import sys
import re
from flask import Flask, jsonify, render_template, url_for, flash, redirect, request, session, g, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_behind_proxy import FlaskBehindProxy
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from forms import RegistrationForm, LoginForm
from functools import wraps
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
def root():
    return redirect(url_for('home'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = Users.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already taken. Please use a different email.', 'danger')
            return redirect(url_for('register'))
        user = Users(name=form.full_name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.email.data}!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.user_id
            flash(f'Login successful for {form.email.data}', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    print("User ID after logout:", session.get('user_id'))
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/voice')
def voice():
    return render_template('voice.html', title='Record')


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


# Get user's token.json from db record. Return None if none exists
def get_user_token(uid):
    user = Users.query.filter_by(user_id=uid).first()
    print(user, file=sys.stderr)
    print(user.token, file=sys.stderr)
    if user and user.token:
        user_token = json.loads(user.token)
        print("user token after", file=sys.stderr)
        return Credentials.from_authorized_user_info(user_token)
    return None


# Save user's token.json to db record
def save_user_token(uid, creds):
    user = Users.query.filter_by(user_id=uid).first()
    if user:
        user.token = creds.to_json()
        db.session.commit()


def google_setup():
    """
    Google Auth & Service.
    """
    def get_google_service():
        print("google_setup route hit", file=sys.stderr)
        if hasattr(g, 'service'):
            print("Service already exists", file=sys.stderr)
            return
        print("Service does not exist", file=sys.stderr)
        user_id = session['user_id']  # Mock user
        print("1", file=sys.stderr)
        creds = get_user_token(user_id)
        print("2", file=sys.stderr)

        if not creds or not creds.valid:
            print("3", file=sys.stderr)
            if creds and creds.expired and creds.refresh_token:
                print("4", file=sys.stderr)
                creds.refresh(Request())
                print("5", file=sys.stderr)
                save_user_token(user_id, creds)
                print("6", file=sys.stderr)
            else:
                print("7", file=sys.stderr)
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                print("8", file=sys.stderr)
                creds = flow.run_local_server(port=8080)
                print("9", file=sys.stderr)
                save_user_token(user_id, creds)
                print("10", file=sys.stderr)

        return build("calendar", "v3", credentials=creds)
    if not hasattr(g, 'service'):
        print("0", file=sys.stderr)
        # global used throughout gcal, gmeet, and/or gmail
        g.service = get_google_service()


def determine_query_type(message: str):
    try:
        print("determine_query_type route hit", file=sys.stderr)
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

                            'mode': } where type is gcal, gmeet, or gmail. If the type is gcal or gmeet, the mode
                            can be create, update, or remove. For email, the mode can be create, update, or send. 
                            """},

                {"role": "user", "content": f"The message is the following: {message}"}
            ]
        )

        response = completion.choices[0].message.content

        # Ensure the response is a JSON string
        response = response[response.index(
            "{"):len(response) - response[::-1].index("}")]
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
        print("gpt_format_json route hit", file=sys.stderr)

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

        '''
        # Ensure the response is a JSON string
        response = response[response.index("{"):len(response) - response[::-1].index("}")]
        # Fixes the capitalization of True in the response
        response = re.sub(r"\btrue\b", "True", response)
        # Evaluate to dictionary
        response = eval(response)

        '''

        return json.loads(response)
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
    try:
        google_setup()
        print(prompt_dictionary)

        # Send success message to chat reciever-end
        print(f"Event Type: {event_type}, Mode: {mode}")
        socketio.emit('receiver', {'message': f"Event Type: {event_type}, Mode: {mode}"})
        success_message = eval(f"{event_type}_{mode}()")
        
        return success_message

    except Exception as e:
        failure_message = """Please try again. The program only works for GCal -> (Create, Update, and Remove),
              GMeet -> (Create, Update, or Remove), or Gmail -> (Create, Update, Send, and Delete)"""
        print("Exception thrown in handle_user_prompt at bottom try-catch",
              file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        return failure_message

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
    print("update_event route hit", file=sys.stderr)
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
    print("format_system_instructions_for_event route hit", file=sys.stderr)
    timeZone = get_localzone()
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    summary = content_dict.get('summary') if content_dict else '<summary_here>'
    description = content_dict.get(
        'description') if content_dict else '<extra specifications, locations, and descriptions here>'
    start = content_dict.get(
        'start') if content_dict else f'start time default {current_datetime}-04:00'
    end = content_dict.get(
        'end') if content_dict else f'end time default {current_datetime}-04:00'

    format_instruction = f"""
    You are an assistant that {query_type_dict.get('mode')}s a Google Calendar event using a sample JSON..
    {'Update only the specified information from user message, leave the rest' if query_type_dict.get('mode') == 'update' else ''}
    Ensure the summary and description are professional and informative. Use default start/end times if none are provided.
    If a start time is provided without an end time, set the end time to 30 minutes after the start time. If there isnt enough 
    information to fill the dictionary, return {'error': 'invalid'}
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

    print("gcal_create route hit", file=sys.stderr)
    prompt_dict = session.get('prompt_dictionary')

    # GPT instructions
    format_instruction = format_system_instructions_for_event(prompt_dict)

    if hasattr(format_instruction, 'error'):
        print("Not enough info. Please try again")
        return 
    


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

    event_description = f"""Event Created! Check your Google Calendar to confirm!\nEvent Details:\n
    Title: {new_event.title}
    Description: {new_event.description}
    Start Time: {new_event.start}
    End Time: {new_event.end}
    """
    socketio.emit('receiver', {'message': event_description})
    print("event created!")


def gcal_update():
    prompt_dict = session.get('prompt_dictionary')
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    # Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    # Limit search to user
    events = Events.query.filter_by(user_id=user_id).all()
    print(Events.query.filter_by(user_id=user_id).first().event_id)
    if not events:
        print("Events not found in db. Try again?")
        socketio.emit('receiver', {'message': 'Events not found in db. Try again?'})
        return

    # Filter events then send to API to find id
    filtered_events = [[{"event_id": event.event_id}, event.event_dictionary] for event in events if any(
        keyword.lower() in event.title.lower() or keyword.lower() in event.description.lower() for keyword in keywords)]
    print(filtered_events)

    if not filtered_events:
        print("No events found matching the provided keywords.", file=sys.stderr)
        socketio.emit('receiver', {'message': 'No matching events found.'})
        return "No matching events found."

    event_id = find_event_id(user_prompt, filtered_events)
    print(event_id)
    if event_id == 'invalid':
        print("Not enough information, please try again?")
        socketio.emit('receiver', {'message': 'Not enough information, please try again?'})
        return
    # query event from database

    #event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    event = Events.query.filter_by(event_id=event_id.replace('\'', '')).first()

    print(event)

    # if not found in db
    if not event:
        print("Event not found in db. Try again?")
        socketio.emit('receiver', {'message': 'Event not found in db. Try again?'})
        return

    event_content = event.serialize()

    event_id = event.event_id

    # GPT instructions
    format_instruction = format_system_instructions_for_event(
        prompt_dict, event_content)

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

    event_description = f"""Event Updated! Check your Google Calendar to confirm!\nEvent Details:\n
    Title: {event.title}
    Description: {event.description}
    Start Time: {event.start}
    End Time: {event.end}
    """
    print("Event has been updated successfully.")
    socketio.emit('receiver', {'message': event_description})


def gcal_remove():
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    # Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    # Limit search to user
    events = Events.query.filter_by(user_id=user_id).all()
    print(Events.query.filter_by(user_id=user_id).first().event_id)
    if not events:
        print("Events not found in db. Try again?")
        socketio.emit('receiver', {'message': 'Events not found in db. Try again?'})
        return

    # Filter events then send to API to find id
    filtered_events = [[{"event_id": event.event_id}, event.event_dictionary] for event in events if any(
        keyword.lower() in event.title.lower() or keyword.lower() in event.description.lower() for keyword in keywords)]
    print(filtered_events)

    if not filtered_events:
        print("No events found matching the provided keywords.", file=sys.stderr)
        socketio.emit('receiver', {'message': 'No matching events found.'})
        return "No matching events found."

    event_id = find_event_id(user_prompt, filtered_events)
    print(event_id)
    if event_id == 'invalid':
        print("Not enough information, please try again?")
        socketio.emit('receiver', {'message': 'Not enough information, please try again?'})
        return
    # query event from database

    #event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    event = Events.query.filter_by(event_id=event_id.replace('\'', '')).first()

    print(event)

    # remove it from calendar
    remove_event(g.service, event.event_id)

    event_description = f"""Event Deleted! \nEvent Details:\n
    \nTitle: {event.title}
    \nDescription: {event.description}
    \nStart Time: {event.start}
    \nEnd Time: {event.end}
    """

    # remove from our db
    db.session.delete(event)
    db.session.commit()

    print("Event has been deleted successfully.")
    socketio.emit('receiver', {'message': event_description})

    return event_description

    


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
    start = content_dict.get(
        'start') if content_dict else 'start time example format <2015-05-28T09:00:00-07:00>'
    end = content_dict.get(
        'end') if content_dict else 'end time example format <2015-05-28T17:00:00-07:00>'
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
    Ensure the summary and description are professional and informative. Use default start/end times if none are provided. If a start time is provided without an end time, set the end time to 30 minutes after the start time. 
    If there isnt enough information to fill in the dictionary, return {{'error': 'invalid'}}. 
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
    print(instructions)
    
    event_data = gpt_format_json(instructions, prompt_dict['prompt'])
    if event_data.get('error'):
        print("Not enough information, Please try again")
        return

    print(event_data)

    event = create_google_meet(g.service, event_data)

    # Create new Meet for our db
    new_meeting = Meets(
        user_id=session['user_id'],
        summary=event_data.get('summary'),
        description=event_data.get('description'),
        start=event_data.get('start').get('dateTime'),
        end=event_data.get('end').get('dateTime'),
        meet_id=event.get('id'),
        attendees=json.dumps((event_data.get('attendees'))),
        meet_dictionary=json.dumps(event_data)
    )

    db.session.add(new_meeting)
    db.session.commit()

    event_description = f"""Meeting created! \nEvent Details:\n
    \nTitle: {new_meeting.summary}
    \nDescription: {new_meeting.description}
    \nStart Time: {new_meeting.start}
    \nEnd Time: {new_meeting.end}
    """
    print("Meeting has been created successfully.")

    socketio.emit('receiver', {'message': event_description})
    
    
def gmeet_update():
    prompt_dict = session.get('prompt_dictionary')
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    # Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    # Limit search to user
    meetings = Meets.query.filter_by(user_id=user_id).all()
    print(Meets.query.filter_by(user_id=user_id).first().meet_id)
    if not meetings:
        print("Meetings not found in db. Try again?")
        return

    # Filter events then send to API to find id
    filtered_meetings = [[{"meet_id": meeting.meet_id}, meeting.meet_dictionary] for meeting in meetings if any(
        keyword.lower() in meeting.summary.lower() or keyword.lower() in meeting.description.lower() for keyword in keywords)]
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
    # event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    meeting = Meets.query.filter_by(meet_id=meet_id.replace('\'', '')).first()
    print(meeting)

    # if not found in db
    if not meeting:
        print("Meeting not found in db. Try again?")
        return

    meeting_content = meeting.serialize()
    print(meeting_content)

    # backtick convention for splitting attendees column
    meeting_content['attendees'] = meeting_content['attendees'].split('`')
    meeting_id = meeting.meet_id

    # instructions if either update or create
    instructions = format_system_instructions_for_meeting(
        prompt_dict, meeting_content)

    # formatted response from gpt --> can be passed directly into create or remove
    # CHECKOUT (why 'title' instead of 'prompt')
    event_data = gpt_format_json(instructions, prompt_dict.get('prompt'))

    event = update_google_meet(g.service, meeting_id, event_data)

    # meeting is current entry
    meeting.summary = event_data.get('summary')
    meeting.description = event_data.get('description')
    meeting.start = event_data.get('start').get('dateTime')
    meeting.end = event_data.get('end').get('dateTime')
    meeting.meet_id = event.get('id')
    meeting.attendees = json.dumps(event_data.get('attendees'))
    meeting.meet_dictionary = json.dumps(event_data)

    db.session.commit()

    event_description = f"""Meeting updated! \nEvent Details:\n
    \nTitle: {meeting.summary}
    \nDescription: {meeting.description}
    \nStart Time: {meeting.start}
    \nEnd Time: {meeting.end}
    """

    print("Meeting updated successfully.")

    socketio.emit('receiver', {'message': event_description})

def gmeet_remove():
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    # Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    # Limit search to user
    meetings = Meets.query.filter_by(user_id=user_id).all()
    print(Meets.query.filter_by(user_id=user_id).first().meet_id)
    if not meetings:
        print("Meetings not found in db. Try again?")
        return

    # Filter events then send to API to find id
    filtered_meetings = [[{"meet_id": meeting.meet_id}, meeting.meet_dictionary] for meeting in meetings if any(
        keyword.lower() in meeting.summary.lower() or keyword.lower() in meeting.description.lower() for keyword in keywords)]
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
    # event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    meeting_to_remove = Meets.query.filter_by(
        meet_id=meet_id.replace('\'', '')).first()
    print(meeting_to_remove)

    # remove it from calendar
    delete_google_meet(g.service, meeting_to_remove.meet_id)

    # remove from our db
    db.session.delete(meeting_to_remove)
    db.session.commit()


    event_description = f"""Meeting removed! \nEvent Details:\n
    \nTitle: {meeting_to_remove.summary}
    \nDescription: {meeting_to_remove.description}
    \nStart Time: {meeting_to_remove.start}
    \nEnd Time: {meeting_to_remove.end}
    """
    print("Meeting removed successfully.")
    socketio.emit('receiver', {'message': event_description})


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
    from_field = email_json['from']  # Assuming `from_list` has a single email
    to_field = email_json['to']
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
    subject = content_dict.get(
        'subject') if content_dict else '<email_subject>'
    body = content_dict.get('body') if content_dict else '<email_body>'
    sender = content_dict.get(
        'from', 'noreply@example.com') if content_dict else 'noreply@example.com'
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
        draft = service.users().drafts().update(
            userId='me', id=draft_id, body=message).execute()
        return draft
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def send_gmail_draft(service, draft_id):
    try:
        # draft =
        service.users().drafts().send(
            userId='me', body={'id': draft_id}).execute()
        print("Draft sent successfully")
        # return draft
    except Exception as e:
        print(f"An error occurred: {e}")


def delete_gmail_draft(service, draft_id):
    try:
        # Delete the draft
        service.users().drafts().delete(userId='me', id=draft_id).execute()
        print("Draft deleted successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")


# @socketio('approval-request-response')
def handle_approval_response(response):
    status = response.get('status')
    email_json = response.get('email')
    if email_json and (status == 'save' or status == 'send'):
        email_raw = email_json_to_raw(email_json)
        draft = create_gmail_draft(g.service, email_raw)
        draft_id = draft.get('id')
        if status == 'send':
            send_gmail_draft(g.service, draft_id)
            print("Gmail draft created successfully")
        elif status == 'save':
            # add stuff here for other fields

            newly_drafted_email = Emails(
                subject=email_json['subject'],
                body=email_json['body'],
                to=email_json['to'],

                user_id=session['user_id'],
                sender=get_authenticated_user_email(g.service),
                cc=email_json.get('cc'),
                email_id=draft.get('id'),
                email_dictionary=json.dumps(email_json),
            )
            db.session.add(newly_drafted_email)
            db.session.commit()
    # technically there is a 'quit' but it's not anywhere, so we just ignore the data


# Creates a draft (not message to allow for updating before sending)
def gmail_create():
    prompt_dict = session.get('prompt_dictionary')
    prompt = prompt_dict.get('prompt')

    content_dict = {'from': f"{get_authenticated_user_email(g.service)}"}
    instructions = format_system_instructions_for_gmail(
        prompt_dict, content_dict)

    created_email_json = gpt_format_json(instructions, prompt)

    socketio.emit('request-approval', created_email_json)


# Sends a draft
def gmail_send():
    # title is key of subject in determine_query_type
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    # Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    # Limit search to user
    emails = Emails.query.filter_by(user_id=user_id).all()
    print(Emails.query.filter_by(user_id=user_id).first().email_id)
    if not emails:
        print("Emails not found in db. Try again?")
        return

    # Filter events then send to API to find id
    filtered_emails = [[{"meet_id": email.email_id}, email.email_dictionary] for email in emails if any(
        keyword.lower() in email.summary.lower() or keyword.lower() in email.description.lower() for keyword in keywords)]
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
    # event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    email_to_send = Emails.query.filter_by(
        email_id=email_id.replace('\'', '')).first()
    print(email_to_send)

    if email_to_send:
        send_gmail_draft(g.service, email_to_send.email_id)

        # remove from db bc its sent, so you can't edit it again anyway
        db.session.delete(email_to_send)
        db.session.commit()


def gmail_delete():
    user_prompt = session['prompt_dictionary']['prompt']
    user_id = session['user_id']

    # Find keywords from prompt
    keywords = extract_keywords(user_prompt)
    print(keywords)

    # Limit search to user
    emails = Emails.query.filter_by(user_id=user_id).all()
    print(Emails.query.filter_by(user_id=user_id).first().email_id)
    if not emails:
        print("Emails not found in db. Try again?")
        return

    # Filter events then send to API to find id
    filtered_emails = [[{"meet_id": email.email_id}, email.email_dictionary] for email in emails if any(
        keyword.lower() in email.summary.lower() or keyword.lower() in email.description.lower() for keyword in keywords)]
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
    # event = Events.query.filter_by(title=prompt_dict.get('title')).first()
    draft_to_delete = Emails.query.filter_by(
        email_id=email_id.replace('\'', '')).first()
    print(draft_to_delete)
    if draft_to_delete:
        # delete from our db
        draft_id = draft_to_delete.email_id
        delete_gmail_draft(g.gmail_service, draft_id)
        db.session.delete(draft_to_delete)
        db.session.commit()


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
