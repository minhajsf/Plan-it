# <img src = "static/img/AssetNew.png"/>
A web-application for managing the Google Workspace using OpenAI API and Google Workspace API.

**Plan-it** serves as your virtual Google assistant! Enabling you to manage your Google Workspace via natural human language.

Make scheduling events, planning virtual meets, and writing up emails easy! Just ask, and **Plan-it** will do all of the work for you.


## Key Features

### Google Calendar:
- Create: Create a new calendar event
- Update: Update an existing event
- Remove: Remove an event from your calendar

###  Google Meets:
- Create: Create a new virtual meet on your calendar
- Update: Update an existing meeting (attendees, title, time, etc...)
- Remove: Remove a meet from your calendar

### Gmail:
- Write: Have AI create a professional draft
- Review: Review the auto-generated draft and edit in-line
- Send or Save: Send your draft or save it for later


## Plan-it vs. Gemini
### 1. Retrieval of Event Details:
**Gemini** \- seperate calls to get event details.

**"Plan-it"** \- only one call! The app's AI autopopulates all of the details based on the user's prompt.

### 2. In-App Functionality
**Gemini** \- must be used in the Gmail app as a writing-aid.

**"Plan-it"** \- functionality works in-app. Stay in one place!
<br>

## Technologies Used:
  
<div>
  <h3><strong>Frontend:</strong></h3>
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white"/>
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white"/>
  <img src="https://img.shields.io/badge/JavaScript-323330?style=for-the-badge&logo=javascript&logoColor=F7DF1E"/>
</div>
  
<div>
  <h3><strong>Backend:</strong></h3>
  <img src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue"/>
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white"/>
  <img src= "https://img.shields.io/badge/Socket.io-010101?&style=for-the-badge&logo=Socket.io&logoColor=white"/> 
</div>

<div style="display: inline-block; text-align: center;">
  <h3><strong>Database:</strong></h3>
  <img src = "https://img.shields.io/badge/Sqlite-003B57?style=for-the-badge&logo=sqlite&logoColor=white"/>
</div>
<div>
  <h3><strong>APIs:</strong></h3>
  <img src = "https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white"/>
  <img src = "https://img.shields.io/badge/ChatGPT-74aa9c?style=for-the-badge&logo=openai&logoColor=white"/>
</div>
<br>


## Using "Plan-it"

To run, follow these steps:
1. **Clone repository into your IDE:**
   ```
   git clone <repository_url>
   ```
2. **Create your virtual environment:** Set up your virtual environment (venv) using 'requirements.txt' as your dependency
   ```
   python -m venv .venv
   ```
3. **Install all libraries:** Install all required libraries by running:
   ```
   pip install -r requirements.txt
   ```
5. **Resolve any imports:** if you encounter any missing imports or any ChatGPT related issues (see ChatGPT for help) install by running:
   ```
   pip install <library_name_here>
   ```
7. **Run your application:** Run app.py within your venv
   ```
   python app.py
   ```
8. **Acess the Application:** Go to your local host url in your web browser:
   ```
   http://127.0.0.1:5000
   ```
   **Note:** This application requires both the OpenAI API and Google Workspace API. Ensure you have valid API keys for these services and set them up in your environment variables as described in the documentation.
    
Enjoy using "Plan-it" :)
