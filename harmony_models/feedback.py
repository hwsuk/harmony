import datetime
import mongoengine


class FeedbackVote(mongoengine.EmbeddedDocument):
    discord_username = mongoengine.StringField(required=True)
    vote_timestamp = mongoengine.DateTimeField(default=datetime.datetime.utcnow)
    vote_weight = mongoengine.IntField(required=True, max_value=1, min_value=-1)


class FeedbackItem(mongoengine.Document):
    author_username = mongoengine.StringField(required=True)
    creation_timestamp = mongoengine.DateTimeField(default=datetime.datetime.utcnow)
    feedback_title = mongoengine.StringField(required=True, max_length=200)
    feedback_description = mongoengine.StringField(required=True, max_length=1500)
    discord_message_id = mongoengine.LongField(required=True, unique=True)
    votes = mongoengine.EmbeddedDocumentListField(FeedbackVote, default=[])
