import json
import typing

import praw.models
import prawcore.exceptions

from loguru import logger

with open('./config.json', 'r') as config_file:
    config = json.load(config_file)

reddit = praw.Reddit(
    client_id=config['reddit']['client_id'],
    client_secret=config['reddit']['client_secret'],
    username=config['reddit']['username'],
    password=config['reddit']['password'],
    user_agent=config['reddit']['user_agent'],
    check_for_async=False
)

verification_message_template = None


def load_verification_message_template() -> None:
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


def create_verification_message(username: str, verification_code: str) -> str:
    """
    Use the previously loaded verification template to generate a verification message.
    :param username: The username to include in the message.
    :param verification_code: The verification code to include in the message.
    :return: The completed verification message.
    """
    global verification_message_template

    message = str(verification_message_template)
    return message.replace("$_username", username).replace("$_verification_code", verification_code)


def reddit_user_exists(username: str) -> bool:
    """
    Check if a Reddit user exists.
    :param username: The username, not beginning with u/, of the Reddit user to check.
    :return: True if the Redditor exists, False otherwise.
    """
    try:
        reddit.redditor(username).id
    except prawcore.exceptions.NotFound:
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


def send_verification_message(username: str, verification_code: str) -> None:
    """
    Send a message to the user with their verification code in it.
    :param username: The user to send the message to.
    :param verification_code: The verification code to include in the message.
    :return: Nothing.
    """

    if not reddit_user_exists(username):
        raise RuntimeError("The specified Reddit user doesn't exist.")

    redditor = get_redditor(username)

    message_contents = create_verification_message(username, verification_code)

    redditor.message(subject="Your /r/HardwareSwapUK Discord verification code", message=message_contents)


def update_user_flair(username: str, flair_text: str, css_class_name: str) -> None:
    """
    Update a user's flair.
    :param username: The username of the user whose flair should be updated.
    :param flair_text: The new flair text.
    :param css_class_name: The CSS class name to apply to the new flair.
    :return: Nothing.
    """

    if not reddit_user_exists(username):
        raise RuntimeError("The specified Reddit user doesn't exist.")

    subreddit = get_subreddit(config["reddit"]["subreddit_name"])
    subreddit.flair.set(username, flair_text, css_class=css_class_name)


load_verification_message_template()
