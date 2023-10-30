import typing
import mongoengine
import harmony_models.verify as verify_models
import harmony_models.feedback as feedback_models
import harmony_models.message_rate_limiter as message_rate_limiter_models

from harmony_config import config

db_name = config.get_configuration_key("db.db_name", required=True)
db_host = config.get_configuration_key("db.hostname", required=True)
db_port = config.get_configuration_key("db.port", required=True, expected_type=int)
db_username = config.get_configuration_key("db.username", required=True)
db_password = config.get_configuration_key("db.password", required=True)
db_replica_set = config.get_configuration_key("db.replica_set_name")

_mongodb_connection_string = f"mongodb://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

if db_replica_set:
    _mongodb_connection_string += f"?replicaSet={db_replica_set}"

connection = mongoengine.connect(
    host=_mongodb_connection_string
)


def get_pending_verification(discord_user_id: int) -> typing.Optional[verify_models.PendingVerification]:
    """
    Fetch a pending verification from the database.
    :param discord_user_id: The Discord user to fetch the pending verification for.
    :return: The pending verification, if found, otherwise None.
    """
    return verify_models.PendingVerification.objects(discord_user__discord_user_id=discord_user_id).first()


def has_pending_verification(discord_user_id: int) -> bool:
    """
    Check if a Discord user has a pending verification.
    :param discord_user_id: The user ID to check.
    :return: True if the user has a pending verification, otherwise False.
    """
    return get_pending_verification(discord_user_id) is not None


def get_verification_data(discord_user_id: int = None,
                          reddit_username: str = None) -> typing.Optional[verify_models.VerifiedUser]:
    """
    Fetch a Discord user's verification data from the database.
    :param discord_user_id: The Discord user ID to fetch the verification for.
    :param reddit_username: The Reddit username to fetch the verification for.
    :return: The verification data, if found, otherwise None.
    """
    if discord_user_id:
        return verify_models.VerifiedUser.objects(discord_user__discord_user_id=discord_user_id).first()
    if reddit_username:
        return verify_models.VerifiedUser.objects(reddit_user__reddit_username__iexact=reddit_username).first()

    return None


def get_all_verification_data() -> typing.List[verify_models.VerifiedUser]:
    """
    Fetch all verified users.
    :return: A list of all verified users.
    """
    return verify_models.VerifiedUser.objects()


def has_verification_data(discord_user_id: int) -> bool:
    """
    Check if a Discord user has verification data.
    :param discord_user_id: The user ID to check.
    :return: True if the user has verification data, otherwise False.
    """
    return get_verification_data(discord_user_id=discord_user_id) is not None


def get_feedback_data(message_id: int) -> typing.Optional[feedback_models.FeedbackItem]:
    """
    Fetch feedback data by the message ID containing its voting view.
    :param message_id: The message ID to fetch.
    :return: The feedback item, if it exists.
    """
    return feedback_models.FeedbackItem.objects(discord_message_id=message_id).first()


def delete_feedback_data(message_id: int) -> typing.NoReturn:
    """
    Delete feedback data by the message ID containing its voting view.
    :param message_id: The feedback data to delete, by the Discord message ID containing its voting view.
    :return: Nothing.
    """
    feedback_data = get_feedback_data(message_id)

    if feedback_data:
        feedback_data.delete()


def save_rate_limiter_message_data(message_author: str, guild_channel_id: int) -> typing.NoReturn:
    """
    Create a message rate limiter data object.
    :param message_author: The username of the message author.
    :param guild_channel_id: The channel ID that the message was sent in.
    :return: Nothing.
    """
    message_rate_limiter_models.MessageRateLimitItem(
        author_username=message_author,
        guild_channel_id=guild_channel_id
    ).save()


def get_rate_limiter_message_data(message_author: str, guild_channel_id: int) \
        -> typing.Optional[message_rate_limiter_models.MessageRateLimitItem]:
    """
    Get a message rate limiter data object.
    :param message_author: The username of the message author.
    :param guild_channel_id: The channel ID that the message was sent in.
    :return: The rate limiter data object if found, otherwise None.
    """
    return message_rate_limiter_models.MessageRateLimitItem.objects(
        author_username=message_author,
        guild_channel_id=guild_channel_id
    ).first()
