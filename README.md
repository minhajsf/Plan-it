# "Plan-it"
A web-application for managing the Google Workspace using OpenAI API and Google Workspace API.

"Plan-it" is your virtual Google assistant! Manage your Google Workspace via natural human language, à la Google Gemini.

Make scheduling events, planning virtual meets, and writing up emails easy! Just ask, and "Plan-it" will do all of the work for you.


# Functionalities -

Google Calendar:
- Create: Create a new calendar event
- Update: Update an existing event
- Remove: Remove an event from your calendar

Google Meets:
- Create: Create a new virtual meet on your calendar
- Update: Update an existing meeting (attendees, title, time, etc...)
- Remove: Remove a meet from your calendar

Gmail:
- Write: Have AI create a professional draft
- Review: Review the auto-generated draft and edit in-line
- Send or Save: Send your draft or save it for later


# "Plan-it" vs. gemini
Gemini \- seperate calls to get event details.

\"Plan-it\" \- only one call! The app's AI autopopulates all of the details based on the user's prompt.

----------------

Gemini \- must be used in the GMail app as a writing-aid.

\"Plan-it\" \- functionality works in-app. Stay in one place!


# Using "Plan-it"

TO RUN:
1. Clone repository into your IDE
2. Create your virutal environment (venv) using 'requirements.txt' as your dependency
3. Install all libraries by running % pip install -r requirements.txt
4. Resolve any imports (see ChatGPT for help) by running % pip install <library_name_here>
5. Run app.py within your venv
6. Go to your local host url (http://127.0.0.1:5000) in your web browser
7. Enjoy using "Plan-it" :)
