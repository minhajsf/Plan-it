from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum

db = SQLAlchemy()


class Event(db.Model):
    """
    Table for Events
    """
    __tablename__ = "event_list"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    start = db.Column(db.String, nullable=False)
    end = db.Column(db.String, nullable=False)
    event_id = db.Column(db.Integer, nullable=False)
    event_dictionary = db.Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes Event object.
        """
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
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "event_id": self.event_id,
            "event_dictionary": self.event_dictionary
        }
