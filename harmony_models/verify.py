import datetime
import mongoengine


class DiscordUser(mongoengine.EmbeddedDocument):
    discord_user_id = mongoengine.IntField(required=True, unique=True)
    guild_roles = mongoengine.ListField(mongoengine.IntField(), default=list)


class RedditUser(mongoengine.EmbeddedDocument):
    reddit_user_id = mongoengine.StringField(required=True, unique=True)
    reddit_username = mongoengine.StringField(required=True)


class UserVerificationData(mongoengine.EmbeddedDocument):
    requested_verification_at = mongoengine.DateTimeField(required=True)
    verified_at = mongoengine.DateTimeField(default=datetime.datetime.now)


class PendingVerificationData(mongoengine.EmbeddedDocument):
    requested_verification_at = mongoengine.DateTimeField(default=datetime.datetime.now)
    verification_code = mongoengine.StringField(required=True, unique=True)


class PendingVerification(mongoengine.Document):
    discord_user: DiscordUser = mongoengine.EmbeddedDocumentField(DiscordUser, required=True)
    reddit_user: RedditUser = mongoengine.EmbeddedDocumentField(RedditUser, required=True)
    pending_verification_data: PendingVerificationData = mongoengine.EmbeddedDocumentField(PendingVerificationData, required=True)
    meta = {'collection': 'pending_verifications'}


class VerifiedUser(mongoengine.Document):
    discord_user: DiscordUser = mongoengine.EmbeddedDocumentField(DiscordUser, required=True)
    reddit_user: RedditUser = mongoengine.EmbeddedDocumentField(RedditUser, required=True)
    user_verification_data: UserVerificationData = mongoengine.EmbeddedDocumentField(UserVerificationData, required=True)
    is_legacy_migration = mongoengine.BooleanField(default=False)
    meta = {'collection': 'verified_users'}
