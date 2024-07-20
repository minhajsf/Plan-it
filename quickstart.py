import os
import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_authenticated_user_email(service):
    try:
        profile = service.users().getProfile(userId='me').execute()
        return profile['emailAddress']
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", GMAIL_SCOPES)
            creds = flow.run_local_server(port=8080)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service

def create_email_json(from_list, to, cc, subject, body):
    email = {
        "from": from_list,
        "to": to,
        "cc": cc,
        "subject": subject,
        "body": body
    }
    return email

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

def create_gmail_draft(service, message_body):
    try:
        message = {
            'message': {
                'raw': base64.urlsafe_b64encode(message_body.encode('utf-8')).decode('utf-8')
            }
        }
        draft = service.users().drafts().create(userId='me', body=message).execute()
        return draft
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def update_gmail_draft(service, draft_id, updated_message_body):
    try:
        message = {
            'message': {
                'raw': base64.urlsafe_b64encode(updated_message_body.encode('utf-8')).decode('utf-8')
            }
        }
        draft = service.users().drafts().update(userId='me', id=draft_id, body=message).execute()
        return draft
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def send_gmail_draft(service, draft_id):
    try:
        draft = service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
        return draft
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def main():
    service = get_gmail_service()

    # Create a draft
    create_email = create_email_json(
        from_list=[f"{get_authenticated_user_email(service)}"],
        to=["ajgarvens@gmail.com"],
        cc=["cc@example.com"],
        subject="Test Draft",
        body="This is the body of the email."
    )
    create_body = email_json_to_raw(create_email)
    draft = create_gmail_draft(service, create_body)
    print("Draft created:", json.dumps(draft, indent=2))

    if draft:
        # Update a draft
        draft_id = draft['id']
        update_email = create_email_json(
            from_list=[f"{get_authenticated_user_email(service)}"],
            to=["asher.garvens1@gmail.com"],
            cc=["cc@example.com"],
            subject="Updated Draft",
            body="This is the updated body of the email."
        )
        update_body_raw = email_json_to_raw(update_email)
        updated_draft = update_gmail_draft(service, draft_id, update_body_raw)
        print("Draft updated:", json.dumps(updated_draft, indent=2))

        # Send the draft
        sent_message = send_gmail_draft(service, draft_id)
        print("Draft sent:", json.dumps(sent_message, indent=2))

if __name__ == '__main__':
    main()
