import datetime
import mongoengine


class MessageRateLimitItem(mongoengine.Document):
    author_username = mongoengine.StringField(required=True)
    guild_channel_id = mongoengine.LongField(required=True)
    message_timestamp = mongoengine.DateTimeField(default=datetime.datetime.utcnow)
