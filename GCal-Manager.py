import os 
import openai
import json
from dotenv import load_dotenv
from openai import OpenAI




# Get OPENAI_API_KEY from environment variables
load_dotenv()
my_api_key = os.getenv('OPENAI_API_KEY')


# Create an OpenAPI client using the API key
client = OpenAI(
    api_key=my_api_key,
)


# Get event type from user
eventType = str(input("What type of event would you like to do? (Create, Update, Remove):"))

# Get the user's request
prompt = str(input("enter prompt here:"))


# Insert Event
if eventType == "Create":

    #create a prompt for GPT API
    insert_format_instruction = f"""
    For your response input the following prompt information in the format below as a valid JSON object (start your response at the first left curly brace of the event dictionary): 

    {prompt}

    event = {{
    "summary": "insert_summary_here",
    "location": "street_address, city, state ZIP_code",
    "description": "description_here",
    "start": {{
        "dateTime": "2015-05-28T09:00:00-07:00",
        "timeZone": "America/Los_Angeles"
    }},
    "end": {{
        "dateTime": "2015-05-28T17:00:00-07:00",
        "timeZone": "America/Los_Angeles"
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
    insert_event = service.events().insert(calendarId='primary', body=event_dict).execute()

    # Get event id
    event_id = insert_event['id'] 
    
    print ('Event created: %s', event.get('htmlLink'))

# Update Event
elif eventType == "Update": 

    print("Implement soon")

# Remove Event
elif eventType == "Remove":

    print("Implement soon")

# User inputted incorrect event type
else:

    print("Please try again with a correct event type (Insert, Update, Remove).")
    exit(1)

prompt = "Can you create an event for Check-in with Brooke this Wednesday at 2PM"

#event_id = completion['id']

# print(create_format_instruction)
# edit_format_instruction = None
# remove_format_instruction = None

# from google.oauth2 import service_account
# from googleapiclient.discovery import build

# # Load credentials from a service account key file
# credentials = service_account.Credentials.from_service_account_file(
#     'path/to/your/service-account-key.json',
#     scopes=['https://www.googleapis.com/auth/calendar']
# )

# # Build the Calendar API service
# service = build('calendar', 'v3', credentials=credentials)

# # Example event ID to update
# event_id = 'your_event_id_here'

# # Prepare the update object
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

# event = service.events().insert(calendarId='primary', body=event).execute()
# print 'Event created: %s' % (event.get('htmlLink'))


# Specify the model to use and the messages to send
# completion = client.chat.completions.create(
#     model="gpt-3.5-turbo",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": create_format_instruction}
#     ]
# )
# print(completion.choices[0].message.content) 



# # First retrieve the event from the API.
# event = service.events().get(calendarId='primary', eventId='eventId').execute()

# event['summary'] = 'Appointment at Somewhere'

# updated_event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()

# # Print the updated date.
# print updated_event['updated']