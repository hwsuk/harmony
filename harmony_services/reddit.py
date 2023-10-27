import typing
import datetime
import praw.models
import prawcore.exceptions

from harmony_config import config
from loguru import logger

reddit = praw.Reddit(
    client_id=config.get_configuration_key("reddit.client_id", required=True),
    client_secret=config.get_configuration_key("reddit.client_secret", required=True),
    username=config.get_configuration_key("reddit.username", required=True),
    password=config.get_configuration_key("reddit.password", required=True),
    user_agent=config.get_configuration_key("reddit.user_agent", required=True),
    check_for_async=False
)

verification_message_template = None
subreddit_name = config.get_configuration_key("reddit.subreddit_name", required=True)


def load_verification_message_template() -> typing.NoReturn:
    """
    Load the verification message template as markdown, and verify that it has the correct template variables.
    :return: Nothing.
    """
    global verification_message_template

    if verification_message_template is not None:
        return

    logger.info("Loading verification message template.")

    with open("verification_template.md", "r") as f:
        verification_message_template = f.read()

    if "$_username" not in verification_message_template or "$_verification_code" not in verification_message_template:
        verification_message_template = None
        raise RuntimeError("Verification message template does not contain the correct substitution variables.")


def create_verification_message(
        username: str,
        verification_code: str,
        subreddit_name: str,
        guild_name: str
) -> str:
    """
    Use the previously loaded verification template to generate a verification message.
    :param username: The username to include in the message.
    :param verification_code: The verification code to include in the message.
    :param subreddit_name: The subreddit name to include in the message.
    :param guild_name: The guild name to include in the message.
    :return: The completed verification message.
    """
    global verification_message_template

    message = str(verification_message_template)
    return (message
            .replace("$_username", username)
            .replace("$_verification_code", verification_code)
            .replace("$_subreddit_name", subreddit_name)
            .replace("$_guild_name", guild_name)
            )


def reddit_user_exists(username: str) -> bool:
    """
    Check if a Reddit user exists.
    :param username: The username, not beginning with u/, of the Reddit user to check.
    :return: True if the Redditor exists, False otherwise.
    """
    try:
        reddit.redditor(username).id
    except (prawcore.exceptions.NotFound, AttributeError):
        return False

    return True


def redditor_suspended(username: str) -> bool:
    """
    Check if a Reddit account is suspended.
    :param username: The username to check.
    :return: True if the Redditor has been suspended, otherwise False.
    """
    try:
        redditor = reddit.redditor(username)
        return hasattr(redditor, 'is_suspended') and redditor.is_suspended
    except prawcore.exceptions.NotFound:
        return False


def subreddit_bans(subreddit: str, limit: int = 10000) -> typing.List[praw.models.Redditor]:
    """
    Get a list of banned accounts from the subreddit.
    :param limit: The maximum number of bans to fetch.
    :param subreddit: The subreddit to check.
    :return: A list of up to {limit} banned accounts from the specified subreddit.
    """
    return get_subreddit(subreddit).banned(limit=limit)


def get_redditor(username: str) -> typing.Optional[praw.models.Redditor]:
    """
    Get a specified Redditor.
    :param username: The Redditor's username, not beginning with u/.
    :return: The Redditor, if it exists, otherwise None.
    """
    try:
        return reddit.redditor(username)
    except prawcore.exceptions.NotFound:
        return None


def get_account_age_days(username: str) -> int:
    """
    Get the specified Redditor's account age, in days.
    :param username: The Redditor's username, not beginning with u/.
    :return: The Redditor's account age, in days.
    """
    redditor = get_redditor(username)

    if redditor and hasattr(redditor, "created_utc"):
        account_created_timestamp = datetime.datetime.fromtimestamp(redditor.created_utc, tz=datetime.timezone.utc)
        now_timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

        return (now_timestamp - account_created_timestamp).days
    else:
        raise RuntimeError(f"Failed to fetch data for redditor u/{username}")


def get_subreddit(subreddit: str) -> typing.Optional[praw.models.Subreddit]:
    """
    Get a specified subreddit.
    :param subreddit: The subreddit's name, not beginning with r/.
    :return: The subreddit, if it exists, otherwise None.
    """
    try:
        return reddit.subreddit(subreddit)
    except prawcore.exceptions.NotFound:
        return None


def send_verification_message(
        username: str,
        verification_code: str,
        subreddit_name: str,
        guild_name: str
) -> typing.NoReturn:
    """
    Send a message to the user with their verification code in it.
    :param username: The user to send the message to.
    :param verification_code: The verification code to include in the message.
    :param subreddit_name: The name of the subreddit to include in the message.
    :param guild_name: The name of the guild to include in the message.
    :return: Nothing.
    """

    if not reddit_user_exists(username):
        raise RuntimeError("The specified Reddit user doesn't exist.")

    redditor = get_redditor(username)

    message_contents = create_verification_message(
        username,
        verification_code,
        subreddit_name,
        guild_name
    )

    redditor.message(subject="Your /r/HardwareSwapUK Discord verification code", message=message_contents)


def update_user_flair(username: str, flair_text: str, css_class_name: str) -> typing.NoReturn:
    """
    Update a user's flair.
    :param username: The username of the user whose flair should be updated.
    :param flair_text: The new flair text.
    :param css_class_name: The CSS class name to apply to the new flair.
    :return: Nothing.
    """

    if not reddit_user_exists(username):
        raise RuntimeError("The specified Reddit user doesn't exist.")

    subreddit = get_subreddit(subreddit_name)
    subreddit.flair.set(username, flair_text, css_class=css_class_name)


load_verification_message_template()
