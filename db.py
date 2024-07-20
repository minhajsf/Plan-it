from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class Users(db.Model):
    """
    Table for Users
    """
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"User('{self.email}')"
    
    def __init__(self, **kwargs):
        """
        Inititalizes a User object.
        """
        self.email = kwargs.get("email", "")

    def serialize(self):
        """
        incr serialize User object.
        """

        return{
            "user_id": self.user_id,
            "email": self.email,
        }
    
    def incr_serialize(self):
        """
        incr Serializes a User object so infinte loop does not occur.
        """ 
        return{
            "user_id": self.user_id,
            "eamil": self.email,
        }


class Events(db.Model):
    """
    Table for Events
    """

    __tablename__ = "Events"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)

    event_type = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    start = db.Column(db.String, nullable=False)
    end = db.Column(db.String, nullable=False)
    event_id = db.Column(db.String, nullable=False)
    event_dictionary = db.Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes Event object.
        """
        self.user_id = kwargs.get("user_id", "")
        self.event_type = kwargs.get("event_type", "")
        self.title = kwargs.get("title", "")
        self.description = kwargs.get("description", "")
        self.start = kwargs.get("start", "")
        self.end = kwargs.get("end", "")
        self.event_id = kwargs.get("event_id", "")
        self.event_dictionary = kwargs.get("event_dictionary", "")

    def serialize(self):
        """
        Serializes an Event object.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "event_id": self.event_id,
            "event_dictionary": self.event_dictionary
        }

    def incr_serialize(self):
        """
        Incr Serializes an Event object so an infinite loop does not occur.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "event_id": self.event_id,
            "event_dictionary": self.event_dictionary
        }

class Meets(db.Model):
    """
    Table for Meets
    """

    __tablename__ = "Meets"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, autoincrement=True)

    meet_type = db.Column(db.String, nullable=False)
    summary = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    start = db.Column(db.String, nullable=False)
    end = db.Column(db.String, nullable=False)
    attendees = db.Column(db.String, nullable=False)
    meet_id = db.Column(db.String, nullable=False)
    meet_dictionary = db.Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes Meet object.
        """
        self.user_id = kwargs.get("user_id", "")
        self.meet_type = kwargs.get("meet_type", "")
        self.summary = kwargs.get("summary", "")
        self.description = kwargs.get("description", "")
        self.start = kwargs.get("start", "")
        self.end = kwargs.get("end", "")
        self.attendees = kwargs.get("attendees", "")
        self.meet_id = kwargs.get("meet_id", "")
        self.meet_dictionary = kwargs.get("meet_dictionary", "")

    def serialize(self):
        """
        Serializes an Meet object.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "meet_type": self.meet_type,
            "summary": self.summary,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "attendees": self.attendees,
            "meet_id": self.meet_id,
            "meet_dictionary": self.meet_dictionary
        }

    def incr_serialize(self):
        """
        Incr Serializes an Meet object so an infinite loop does not occur.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "meet_type": self.meet_type,
            "summary": self.summary,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "attendees": self.attendees,
            "meet_id": self.meet_id,
            "meet_dictionary": self.meet_dictionary
        }

class Emails(db.Model):
    """
    Table for Emails
    """
    __tablename__ = "Emails"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, autoincrement=True)
    email_type = db.Column(db.String, nullable=True)
    subject = db.Column(db.String, nullable=False)
    body = db.Column(db.String, nullable=False)
    to = db.Column(db.String, nullable=False)
    sender = db.Column(db.String, nullable=False)
    email_id = db.Column(db.String, nullable=False)
    email_dictionary = db.Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes Email object.
        """
        self.user_id = kwargs.get("user_id", "")
        self.email_type = kwargs.get("email_type", "")
        self.subject = kwargs.get("subject", "")
        self.body = kwargs.get("body", "")
        self.to = kwargs.get("to", "")
        self.sender = kwargs.get("sender", "")
        self.email_id = kwargs.get("email_id", "")
        self.email_dictionary = kwargs.get("email_dictionary", "")

    def serialize(self):
        """
        Serializes an Email object.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_type": self.email_type,
            "subject": self.subject,
            "body": self.body,
            "to": self.to,
            "sender": self.sender,
            "email_id": self.email_id,
            "email_dictionary": self.email_dictionary
        }

    def incr_serialize(self):
        """
        Incr Serializes an Email object so an infinite loop does not occur.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_type": self.email_type,
            "subject": self.subject,
            "body": self.body,
            "to": self.to,
            "sender": self.sender,
            "email_id": self.email_id,
            "email_dictionary": self.email_dictionary
        }
